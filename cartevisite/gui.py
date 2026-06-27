"""Interface graphique tkinter de l'application de numérisation.

L'interface reste volontairement épurée :

* écran principal avec les boutons « Prendre une photo » et « Importer
  un fichier », la liste des contacts et les boutons d'export ;
* fenêtre de validation/édition après chaque scan ;
* fonctionnement dégradé si l'OCR n'est pas disponible (saisie manuelle).

tkinter fait partie de la bibliothèque standard ; ce module ne nécessite
donc aucune dépendance externe pour démarrer.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .database import ContactDatabase
from .export import export_json, export_vcards
from .models import Contact

# Champs éditables présentés à l'utilisateur : (attribut, libellé).
_FIELDS = [
    ("full_name", "Nom complet"),
    ("title", "Fonction / Poste"),
    ("company", "Entreprise"),
    ("phone", "Téléphone"),
    ("email", "E-mail"),
    ("website", "Site web"),
    ("address", "Adresse"),
    ("notes", "Notes"),
]

_IMAGE_TYPES = [
    ("Cartes de visite", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.pdf"),
    ("Images", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
    ("PDF", "*.pdf"),
    ("Tous les fichiers", "*.*"),
]


class ContactEditor(tk.Toplevel):
    """Fenêtre modale de validation/édition d'un contact."""

    def __init__(self, master: tk.Misc, contact: Contact, on_save) -> None:
        super().__init__(master)
        self.title("Vérifier les informations")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._contact = contact
        self._on_save = on_save
        self._vars: dict[str, tk.StringVar] = {}

        frame = ttk.Frame(self, padding=16)
        frame.grid(sticky="nsew")

        ttk.Label(
            frame,
            text="Corrigez les informations détectées si nécessaire :",
            font=("", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 12), sticky="w")

        for i, (attr, label) in enumerate(_FIELDS, start=1):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=3, padx=(0, 8))
            var = tk.StringVar(value=getattr(contact, attr))
            self._vars[attr] = var
            ttk.Entry(frame, textvariable=var, width=42).grid(row=i, column=1, pady=3, sticky="ew")

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(_FIELDS) + 1, column=0, columnspan=2, pady=(14, 0), sticky="e")
        ttk.Button(buttons, text="Annuler", command=self.destroy).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Enregistrer", command=self._save).grid(row=0, column=1, padx=4)

    def _save(self) -> None:
        for attr, _ in _FIELDS:
            setattr(self._contact, attr, self._vars[attr].get().strip())
        if self._contact.is_empty():
            messagebox.showwarning(
                "Contact vide",
                "Aucune information à enregistrer. Renseignez au moins un champ.",
                parent=self,
            )
            return
        self._on_save(self._contact)
        self.destroy()


class App(tk.Tk):
    """Fenêtre principale de l'application."""

    def __init__(self, db_path: str = "contacts.db", export_dir: str = ".") -> None:
        super().__init__()
        self.title("Numérisation de cartes de visite")
        self.geometry("640x460")
        self.minsize(560, 420)

        self.db = ContactDatabase(db_path)
        self.export_dir = export_dir

        self._build_ui()
        self.refresh_list()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- Construction de l'interface ------------------------------------

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self, padding=(10, 10, 10, 4))
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="📷 Prendre une photo", command=self.take_photo).pack(side="left", padx=4)
        ttk.Button(toolbar, text="📁 Importer un fichier", command=self.import_file).pack(side="left", padx=4)
        ttk.Button(toolbar, text="📂 Traiter CV-Scan", command=self.process_folder).pack(side="left", padx=4)
        ttk.Button(toolbar, text="➕ Saisie manuelle", command=self.manual_entry).pack(side="left", padx=4)

        # Liste des contacts.
        list_frame = ttk.Frame(self, padding=(10, 4))
        list_frame.pack(fill="both", expand=True)

        columns = ("name", "company", "email", "phone")
        headings = {"name": "Nom", "company": "Entreprise", "email": "E-mail", "phone": "Téléphone"}
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=150, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())

        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        # Barre d'actions du bas.
        actions = ttk.Frame(self, padding=(10, 4, 10, 10))
        actions.pack(fill="x")
        ttk.Button(actions, text="✏️ Modifier", command=self.edit_selected).pack(side="left", padx=4)
        ttk.Button(actions, text="🗑️ Supprimer", command=self.delete_selected).pack(side="left", padx=4)
        ttk.Button(actions, text="Exporter en JSON", command=self.export_json_action).pack(side="right", padx=4)
        ttk.Button(actions, text="Exporter en vCard", command=self.export_vcf_action).pack(side="right", padx=4)

        self.status = tk.StringVar(value="Prêt.")
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=4).pack(fill="x")

    # -- Données ---------------------------------------------------------

    def refresh_list(self) -> None:
        self.tree.delete(*self.tree.get_children())
        contacts = self.db.all()
        for contact in contacts:
            self.tree.insert(
                "", "end", iid=str(contact.id),
                values=(contact.full_name, contact.company, contact.email, contact.phone),
            )
        self.status.set(f"{len(contacts)} contact(s) en base.")

    def _selected_id(self) -> Optional[int]:
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    # -- Actions de scan -------------------------------------------------

    def take_photo(self) -> None:
        """Capture via webcam (OpenCV) ; repli sur l'import si indisponible."""
        try:
            from .camera import capture_photo
        except Exception:
            messagebox.showinfo(
                "Caméra",
                "Module caméra indisponible. Utilisez « Importer un fichier ».",
            )
            return
        try:
            path = capture_photo()
        except Exception as exc:
            messagebox.showerror("Caméra", f"Échec de la capture : {exc}")
            return
        if path:
            self._scan_file(path)

    def import_file(self) -> None:
        path = filedialog.askopenfilename(title="Choisir une carte", filetypes=_IMAGE_TYPES)
        if path:
            self._scan_file(path)

    def manual_entry(self) -> None:
        ContactEditor(self, Contact(), self._persist_new)

    def process_folder(self) -> None:
        """Traite par lots le dossier ``CV-Scan`` choisi par l'utilisateur.

        Les contacts extraits sont enregistrés en base et exportés en
        JSON + vCard dans les sous-dossiers ``CV-JSON`` et ``CV-VCF``.
        """
        from .batch import SCAN_DIR, find_base_dir

        suggestion = find_base_dir()
        chosen = filedialog.askdirectory(
            title="Choisir le dossier « numérisation » (contenant CV-Scan)",
            initialdir=str(suggestion if suggestion.exists() else Path.home()),
        )
        if not chosen:
            return

        base = Path(chosen)
        # Tolérance : l'utilisateur a pu désigner directement CV-Scan.
        if base.name == SCAN_DIR:
            base = base.parent

        self.status.set("Traitement du dossier CV-Scan en cours…")

        def worker() -> None:
            try:
                from .batch import process_directory
                result = process_directory(base_dir=base, db_path=self.db.path, log=lambda *_: None)
                self.after(0, lambda: self._after_batch(result))
            except Exception as exc:
                self.after(0, lambda: self._scan_failed(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _after_batch(self, result) -> None:
        self.refresh_list()
        if not result.contacts:
            self.status.set("Aucun contact extrait du dossier CV-Scan.")
            messagebox.showinfo("Traitement du dossier", result.summary())
            return
        self.status.set(
            f"{len(result.contacts)} contact(s) extrait(s) et exporté(s)."
        )
        messagebox.showinfo("Traitement du dossier", result.summary())

    def _scan_file(self, path: str) -> None:
        """Lance l'OCR en arrière-plan pour ne pas figer l'interface."""
        self.status.set(f"Analyse de {Path(path).name} en cours…")

        def worker() -> None:
            try:
                from .ocr import scan_to_contact
                contact = scan_to_contact(path)
                self.after(0, lambda: self._after_scan(contact))
            except Exception as exc:
                self.after(0, lambda: self._scan_failed(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _after_scan(self, contact: Contact) -> None:
        self.status.set("Analyse terminée. Vérifiez les informations.")
        ContactEditor(self, contact, self._persist_new)

    def _scan_failed(self, exc: Exception) -> None:
        self.status.set("Échec de l'analyse.")
        if messagebox.askyesno(
            "OCR indisponible",
            f"L'extraction automatique a échoué :\n{exc}\n\n"
            "Voulez-vous saisir le contact manuellement ?",
        ):
            self.manual_entry()

    # -- Persistance -----------------------------------------------------

    def _persist_new(self, contact: Contact) -> None:
        self.db.add(contact)
        self.refresh_list()
        self.status.set(f"Contact « {contact.display_label()} » enregistré.")

    def _persist_update(self, contact: Contact) -> None:
        self.db.update(contact)
        self.refresh_list()
        self.status.set(f"Contact « {contact.display_label()} » mis à jour.")

    def edit_selected(self) -> None:
        contact_id = self._selected_id()
        if contact_id is None:
            messagebox.showinfo("Modifier", "Sélectionnez d'abord un contact.")
            return
        contact = self.db.get(contact_id)
        if contact:
            ContactEditor(self, contact, self._persist_update)

    def delete_selected(self) -> None:
        contact_id = self._selected_id()
        if contact_id is None:
            messagebox.showinfo("Supprimer", "Sélectionnez d'abord un contact.")
            return
        if messagebox.askyesno("Supprimer", "Supprimer définitivement ce contact ?"):
            self.db.delete(contact_id)
            self.refresh_list()
            self.status.set("Contact supprimé.")

    # -- Export ----------------------------------------------------------

    def export_json_action(self) -> None:
        contacts = self.db.all()
        if not contacts:
            messagebox.showinfo("Export JSON", "Aucun contact à exporter.")
            return
        path = export_json(contacts, self.export_dir)
        self.status.set(f"Export JSON : {path}")
        messagebox.showinfo("Export JSON", f"{len(contacts)} contact(s) exporté(s) vers :\n{path}")

    def export_vcf_action(self) -> None:
        contacts = self.db.all()
        if not contacts:
            messagebox.showinfo("Export vCard", "Aucun contact à exporter.")
            return
        paths = export_vcards(contacts, self.export_dir)
        self.status.set(f"Export vCard : {len(paths)} fichier(s).")
        messagebox.showinfo(
            "Export vCard",
            f"{len(paths)} fichier(s) .vcf généré(s) dans le dossier CV-VCF.",
        )

    # -- Fermeture -------------------------------------------------------

    def _on_close(self) -> None:
        self.db.close()
        self.destroy()


def main() -> None:
    """Point d'entrée de l'interface graphique."""
    App().mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
