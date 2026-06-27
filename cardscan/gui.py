"""Interface graphique tkinter de CardScan.

L'interface se veut volontairement épurée : deux gros boutons d'action
(« Prendre une photo », « Importer un fichier »), un écran de validation des
champs détectés, une liste des contacts enregistrés et deux boutons d'export.

Le travail OCR (potentiellement long) est exécuté dans un thread de fond afin
de ne pas geler l'interface ; le résultat est ré-injecté dans le thread Tk via
``after``.

Tkinter fait partie de la bibliothèque standard mais n'est pas toujours
disponible (environnements sans affichage). L'import est donc protégé.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from .contact import Contact
from .database import ContactDatabase
from . import export

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    _TK_AVAILABLE = True
except Exception:  # pragma: no cover - dépend de l'environnement
    _TK_AVAILABLE = False


# Champs éditables affichés dans l'écran de validation : (attribut, libellé).
_FIELDS = [
    ("full_name", "Nom complet"),
    ("company", "Entreprise"),
    ("job_title", "Fonction"),
    ("email", "E-mail"),
    ("phone", "Téléphone"),
    ("website", "Site web"),
    ("address", "Adresse"),
    ("notes", "Notes"),
]


class CardScanApp:
    """Fenêtre principale de l'application."""

    def __init__(self, root: "tk.Tk", db: Optional[ContactDatabase] = None):
        self.root = root
        self.db = db or ContactDatabase()
        self.export_dir = Path.home() / "CardScan"

        self.entries: dict = {}
        self._current_id: Optional[int] = None

        root.title("CardScan – Numérisation de cartes de visite")
        root.geometry("760x560")
        root.minsize(680, 500)

        self._build_ui()
        self.refresh_contacts()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # --- Barre d'actions principale ---------------------------------
        actions = ttk.Frame(self.root, padding=12)
        actions.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(
            actions, text="📷  Prendre une photo", command=self.take_photo
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            actions, text="📂  Importer un fichier", command=self.import_file
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            actions, text="📁  Scanner un dossier", command=self.scan_folder
        ).pack(side=tk.LEFT, padx=4)

        self.status = ttk.Label(actions, text="Prêt.", foreground="#555")
        self.status.pack(side=tk.RIGHT)

        # --- Zone centrale : liste + formulaire -------------------------
        body = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        body.pack(fill=tk.BOTH, expand=True)

        # Liste des contacts (gauche).
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        ttk.Label(left, text="Contacts enregistrés").pack(anchor=tk.W)

        self.listbox = tk.Listbox(left, width=30, activestyle="dotbox")
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        list_actions = ttk.Frame(left)
        list_actions.pack(fill=tk.X)
        ttk.Button(list_actions, text="Nouveau", command=self.new_contact).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(list_actions, text="Supprimer", command=self.delete_contact).pack(
            side=tk.LEFT, padx=2
        )

        # Formulaire de validation/édition (droite).
        right = ttk.Frame(body, padding=(12, 0, 0, 0))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(
            right, text="Informations détectées (modifiables)"
        ).pack(anchor=tk.W)

        form = ttk.Frame(right)
        form.pack(fill=tk.X, pady=6)
        for row, (attr, label) in enumerate(_FIELDS):
            ttk.Label(form, text=label + " :").grid(
                row=row, column=0, sticky=tk.W, pady=3, padx=(0, 8)
            )
            var = tk.StringVar()
            entry = ttk.Entry(form, textvariable=var, width=44)
            entry.grid(row=row, column=1, sticky=tk.EW, pady=3)
            self.entries[attr] = var
        form.columnconfigure(1, weight=1)

        # Boutons de sauvegarde et d'export.
        buttons = ttk.Frame(right)
        buttons.pack(fill=tk.X, pady=8)
        ttk.Button(buttons, text="💾  Enregistrer", command=self.save_contact).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(
            buttons, text="Exporter en JSON", command=self.export_json
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            buttons, text="Exporter en vCard", command=self.export_vcard
        ).pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------
    # Actions OCR
    # ------------------------------------------------------------------
    def take_photo(self) -> None:
        """Capture via webcam si OpenCV est disponible, sinon explique."""
        self._set_status("Ouverture de la caméra…")
        threading.Thread(target=self._capture_photo, daemon=True).start()

    def _capture_photo(self) -> None:
        try:
            from .camera import capture_to_temp

            path = capture_to_temp()
        except Exception as exc:  # noqa: BLE001 - on remonte tout à l'UI
            self.root.after(0, lambda: self._handle_error(exc))
            return
        if path is None:
            self.root.after(0, lambda: self._set_status("Capture annulée."))
            return
        self._run_ocr(path)

    def import_file(self) -> None:
        if not _TK_AVAILABLE:
            return
        path = filedialog.askopenfilename(
            title="Choisir une carte de visite",
            filetypes=[
                ("Images et PDF", "*.jpg *.jpeg *.png *.pdf"),
                ("Tous les fichiers", "*.*"),
            ],
        )
        if path:
            self._set_status("Analyse en cours…")
            threading.Thread(
                target=self._run_ocr, args=(path,), daemon=True
            ).start()

    def _run_ocr(self, path: str) -> None:
        """Exécute l'OCR (thread de fond) puis met à jour le formulaire."""
        try:
            from .ocr import scan_card

            contact = scan_card(path)
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._handle_error(exc))
            return
        self.root.after(0, lambda: self._populate_form(contact, new=True))
        self.root.after(
            0, lambda: self._set_status(f"Carte analysée : {Path(path).name}")
        )

    def scan_folder(self) -> None:
        """Balaye un dossier entier et enregistre toutes les cartes trouvées."""
        if not _TK_AVAILABLE:
            return
        directory = filedialog.askdirectory(
            title="Choisir un dossier contenant des cartes de visite"
        )
        if not directory:
            return
        recursive = messagebox.askyesno(
            "Sous-dossiers",
            "Inclure aussi les sous-dossiers dans le balayage ?",
        )
        self._set_status("Balayage du dossier…")
        threading.Thread(
            target=self._run_folder_scan,
            args=(directory, recursive),
            daemon=True,
        ).start()

    def _run_folder_scan(self, directory: str, recursive: bool) -> None:
        """Analyse en lot (thread de fond) puis enregistre les contacts."""
        try:
            from .scanner import find_card_files, iter_scan_directory
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._handle_error(exc))
            return

        try:
            files = find_card_files(directory, recursive=recursive)
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._handle_error(exc))
            return

        if not files:
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Balayage", "Aucune image ou PDF trouvé dans ce dossier."
                ),
            )
            self.root.after(0, lambda: self._set_status("Dossier vide."))
            return

        total = len(files)
        scanned: list = []
        failed = 0
        for index, result in enumerate(
            iter_scan_directory(directory, recursive=recursive), start=1
        ):
            name = result.path.name
            self.root.after(
                0,
                lambda i=index, n=name: self._set_status(
                    f"Analyse {i}/{total} : {n}"
                ),
            )
            if result.ok and result.contact and not result.contact.is_empty():
                # L'accès à la base se fait depuis le thread de fond ; la
                # connexion SQLite par défaut tolère un seul thread, donc on
                # délègue l'écriture au thread Tk.
                self.root.after(0, self.db.add, result.contact)
                scanned.append(result.contact)
            elif not result.ok:
                failed += 1

        def _finish():
            self.refresh_contacts()
            # Export automatique des cartes balayées dans les deux dossiers
            # dédiés (CV-JSON et CV-VCF), à côté des images d'origine.
            json_path = vcf_dir = None
            if scanned:
                json_path = export.export_json(scanned, directory)
                export.export_vcards(scanned, directory)
                vcf_dir = Path(directory) / export.VCF_DIR_NAME
            summary = (
                f"{len(scanned)} contact(s) enregistré(s) sur {total} fichier(s).\n"
                f"{failed} échec(s) d'analyse."
            )
            if scanned:
                summary += (
                    f"\n\nExports générés :\n"
                    f"• JSON  : {json_path}\n"
                    f"• vCard : {vcf_dir}"
                )
            messagebox.showinfo("Balayage terminé", summary)
            self._set_status(
                f"Balayage terminé : {len(scanned)}/{total} carte(s), "
                f"export JSON + vCard."
            )

        self.root.after(0, _finish)

    # ------------------------------------------------------------------
    # Gestion du formulaire et des contacts
    # ------------------------------------------------------------------
    def _populate_form(self, contact: Contact, new: bool = False) -> None:
        for attr, _ in _FIELDS:
            self.entries[attr].set(getattr(contact, attr, ""))
        self._current_id = None if new else contact.id

    def _form_to_contact(self) -> Contact:
        data = {attr: self.entries[attr].get().strip() for attr, _ in _FIELDS}
        contact = Contact(**data)
        contact.id = self._current_id
        return contact

    def new_contact(self) -> None:
        self._populate_form(Contact(), new=True)
        self.listbox.selection_clear(0, tk.END)
        self._set_status("Nouveau contact.")

    def save_contact(self) -> None:
        contact = self._form_to_contact()
        if contact.is_empty():
            messagebox.showwarning(
                "Contact vide", "Renseignez au moins un champ avant d'enregistrer."
            )
            return
        if contact.id is None:
            self.db.add(contact)
            self._set_status(f"Contact « {contact.display_name()} » ajouté.")
        else:
            self.db.update(contact)
            self._set_status(f"Contact « {contact.display_name()} » mis à jour.")
        self._current_id = contact.id
        self.refresh_contacts(select_id=contact.id)

    def delete_contact(self) -> None:
        if self._current_id is None:
            return
        if not messagebox.askyesno(
            "Supprimer", "Supprimer définitivement ce contact ?"
        ):
            return
        self.db.delete(self._current_id)
        self.new_contact()
        self.refresh_contacts()
        self._set_status("Contact supprimé.")

    def refresh_contacts(self, select_id: Optional[int] = None) -> None:
        self._contacts = self.db.all()
        self.listbox.delete(0, tk.END)
        select_index = None
        for index, contact in enumerate(self._contacts):
            self.listbox.insert(tk.END, contact.display_name())
            if contact.id == select_id:
                select_index = index
        if select_index is not None:
            self.listbox.selection_set(select_index)
            self.listbox.see(select_index)

    def _on_select(self, _event) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        contact = self._contacts[selection[0]]
        self._populate_form(contact, new=False)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def export_json(self) -> None:
        contacts = self.db.all()
        if not contacts:
            messagebox.showinfo("Export", "Aucun contact à exporter.")
            return
        path = export.export_json(contacts, self.export_dir)
        messagebox.showinfo("Export JSON", f"{len(contacts)} contact(s) exporté(s) :\n{path}")
        self._set_status(f"Export JSON : {path}")

    def export_vcard(self) -> None:
        contacts = self.db.all()
        if not contacts:
            messagebox.showinfo("Export", "Aucun contact à exporter.")
            return
        paths = export.export_vcards(contacts, self.export_dir)
        messagebox.showinfo(
            "Export vCard",
            f"{len(paths)} fichier(s) .vcf généré(s) dans :\n{self.export_dir / export.VCF_DIR_NAME}",
        )
        self._set_status(f"Export vCard : {len(paths)} fichier(s).")

    # ------------------------------------------------------------------
    # Divers
    # ------------------------------------------------------------------
    def _set_status(self, text: str) -> None:
        self.status.config(text=text)

    def _handle_error(self, exc: Exception) -> None:
        messagebox.showerror("Erreur", str(exc))
        self._set_status("Erreur : " + str(exc))


def run() -> None:
    """Point d'entrée : lance l'application graphique."""
    if not _TK_AVAILABLE:
        raise RuntimeError(
            "Tkinter n'est pas disponible dans cet environnement. "
            "Installez le paquet système python3-tk."
        )
    root = tk.Tk()
    CardScanApp(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    run()
