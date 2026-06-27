"""Interface graphique tkinter de l'application de numérisation.

L'écran principal présente la liste des contacts et les actions :
  * Importer un fichier (image ou PDF)
  * Prendre une photo (capture caméra si OpenCV est disponible)
  * Modifier / Supprimer un contact
  * Exporter en JSON / vCard

Toute la logique métier vit dans les autres modules ; ce fichier ne fait que
de la présentation et de l'orchestration.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import config, export, ocr
from .database import ContactDatabase
from .models import Contact
from .parser import parse_contact

_FIELDS = [
    ("name", "Nom"),
    ("company", "Société"),
    ("title", "Fonction"),
    ("phone", "Téléphone"),
    ("email", "E-mail"),
    ("website", "Site web"),
    ("address", "Adresse"),
    ("notes", "Notes"),
]


class ContactEditor(tk.Toplevel):
    """Fenêtre modale de validation / édition d'un contact."""

    def __init__(self, master, contact: Contact, on_save):
        super().__init__(master)
        self.title("Vérifier le contact")
        self.contact = contact
        self.on_save = on_save
        self._vars: dict[str, tk.StringVar] = {}
        self.transient(master)
        self.resizable(False, False)
        self._build()
        self.grab_set()

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=16)
        frame.grid(sticky="nsew")

        ttk.Label(
            frame,
            text="Vérifiez les informations détectées, corrigez si besoin :",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        for i, (key, label) in enumerate(_FIELDS, start=1):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="e", padx=(0, 8), pady=3)
            var = tk.StringVar(value=getattr(self.contact, key))
            self._vars[key] = var
            ttk.Entry(frame, textvariable=var, width=42).grid(row=i, column=1, sticky="we", pady=3)

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(_FIELDS) + 1, column=0, columnspan=2, pady=(14, 0), sticky="e")
        ttk.Button(buttons, text="Annuler", command=self.destroy).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Enregistrer", command=self._save).grid(row=0, column=1, padx=4)

    def _save(self) -> None:
        for key, var in self._vars.items():
            setattr(self.contact, key, var.get().strip())
        if self.contact.is_empty():
            messagebox.showwarning(
                "Contact vide", "Renseignez au moins un champ avant d'enregistrer.",
                parent=self,
            )
            return
        self.on_save(self.contact)
        self.destroy()


class App(tk.Tk):
    """Fenêtre principale de l'application."""

    def __init__(self, db: ContactDatabase):
        super().__init__()
        self.db = db
        self.title("Numérisation de cartes de visite")
        self.geometry("720x460")
        self.minsize(620, 400)
        self._build()
        self.refresh()

    # -- Construction de l'UI ----------------------------------------------

    def _build(self) -> None:
        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="📷 Prendre une photo", command=self.take_photo).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📂 Importer un fichier", command=self.import_file).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Modifier", command=self.edit_selected).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Supprimer", command=self.delete_selected).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Exporter JSON", command=self.export_json).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Exporter vCard", command=self.export_vcards).pack(side="left", padx=2)

        # Recherche.
        search_frame = ttk.Frame(self, padding=(10, 0))
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Rechercher :").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side="left", padx=6, pady=6)

        # Tableau des contacts.
        columns = ("name", "company", "title", "phone", "email")
        headers = {"name": "Nom", "company": "Société", "title": "Fonction",
                   "phone": "Téléphone", "email": "E-mail"}
        tree_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=130, anchor="w")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())

        # Barre de statut.
        self.status = tk.StringVar(value="Prêt.")
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w",
                  padding=(8, 2)).pack(fill="x", side="bottom")

    # -- Données ------------------------------------------------------------

    def refresh(self) -> None:
        term = self.search_var.get().strip()
        contacts = self.db.search(term) if term else self.db.all()
        self.tree.delete(*self.tree.get_children())
        for contact in contacts:
            self.tree.insert(
                "", "end", iid=str(contact.id),
                values=(contact.name, contact.company, contact.title, contact.phone, contact.email),
            )
        self.status.set(f"{self.db.count()} contact(s) enregistré(s).")

    def _selected_id(self) -> Optional[int]:
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    # -- Actions : import / OCR --------------------------------------------

    def import_file(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in config.SUPPORTED_EXTENSIONS)
        path = filedialog.askopenfilename(
            title="Choisir une carte de visite",
            filetypes=[("Cartes (images, PDF)", patterns), ("Tous les fichiers", "*.*")],
        )
        if path:
            self._process_path(Path(path))

    def take_photo(self) -> None:
        """Capture une image depuis la webcam (nécessite OpenCV)."""
        try:
            import cv2  # type: ignore
        except ImportError:
            messagebox.showinfo(
                "Caméra indisponible",
                "OpenCV n'est pas installé. Utilisez « Importer un fichier » à la place.",
                parent=self,
            )
            return

        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            messagebox.showerror("Caméra", "Impossible d'accéder à la caméra.", parent=self)
            return
        messagebox.showinfo(
            "Capture", "Cadrez la carte puis appuyez sur ESPACE pour photographier (ÉCHAP pour annuler).",
            parent=self,
        )
        captured = None
        while True:
            ok, frame = cam.read()
            if not ok:
                break
            cv2.imshow("Prendre une photo - ESPACE: capturer / ESC: annuler", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            if key == 32:  # ESPACE
                captured = frame
                break
        cam.release()
        cv2.destroyAllWindows()

        if captured is not None:
            config.ensure_dirs()
            snapshot = config.DATA_DIR / "_capture.png"
            cv2.imwrite(str(snapshot), captured)
            self._process_path(snapshot)

    def _process_path(self, path: Path) -> None:
        if not ocr.ocr_available():
            messagebox.showerror(
                "OCR indisponible",
                "Les dépendances OCR (pytesseract, Pillow et le binaire Tesseract) "
                "ne sont pas installées. Voir le README pour l'installation.",
                parent=self,
            )
            return

        self.status.set(f"Analyse de {path.name}…")
        self.update_idletasks()

        result: dict = {}

        def work() -> None:
            try:
                text = ocr.extract_text(path)
                result["contact"] = parse_contact(text)
            except Exception as exc:  # noqa: BLE001 - remonté à l'utilisateur
                result["error"] = exc

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        self._await_thread(thread, result)

    def _await_thread(self, thread: threading.Thread, result: dict) -> None:
        if thread.is_alive():
            self.after(100, lambda: self._await_thread(thread, result))
            return
        if "error" in result:
            self.status.set("Échec de l'analyse.")
            messagebox.showerror("Erreur OCR", str(result["error"]), parent=self)
            return
        self.status.set("Analyse terminée.")
        contact = result.get("contact") or Contact()
        ContactEditor(self, contact, on_save=self._save_new)

    def _save_new(self, contact: Contact) -> None:
        self.db.add(contact)
        self.refresh()
        self.status.set(f"Contact « {contact.display_name()} » enregistré.")

    # -- Actions : édition / suppression -----------------------------------

    def edit_selected(self) -> None:
        contact_id = self._selected_id()
        if contact_id is None:
            messagebox.showinfo("Sélection", "Sélectionnez d'abord un contact.", parent=self)
            return
        contact = self.db.get(contact_id)
        if contact:
            ContactEditor(self, contact, on_save=self._save_existing)

    def _save_existing(self, contact: Contact) -> None:
        self.db.update(contact)
        self.refresh()
        self.status.set(f"Contact « {contact.display_name()} » mis à jour.")

    def delete_selected(self) -> None:
        contact_id = self._selected_id()
        if contact_id is None:
            messagebox.showinfo("Sélection", "Sélectionnez d'abord un contact.", parent=self)
            return
        if messagebox.askyesno("Supprimer", "Supprimer ce contact ?", parent=self):
            self.db.delete(contact_id)
            self.refresh()
            self.status.set("Contact supprimé.")

    # -- Actions : export ---------------------------------------------------

    def export_json(self) -> None:
        contacts = self.db.all()
        if not contacts:
            messagebox.showinfo("Export", "Aucun contact à exporter.", parent=self)
            return
        config.ensure_dirs()
        path = export.export_json(contacts, config.JSON_EXPORT_DIR)
        self.status.set(f"Export JSON : {path}")
        messagebox.showinfo("Export JSON", f"{len(contacts)} contact(s) exporté(s) vers :\n{path}", parent=self)

    def export_vcards(self) -> None:
        contacts = self.db.all()
        if not contacts:
            messagebox.showinfo("Export", "Aucun contact à exporter.", parent=self)
            return
        config.ensure_dirs()
        paths = export.export_vcards(contacts, config.VCF_EXPORT_DIR)
        self.status.set(f"Export vCard : {len(paths)} fichier(s) dans {config.VCF_EXPORT_DIR}")
        messagebox.showinfo(
            "Export vCard",
            f"{len(paths)} fichier(s) .vcf généré(s) dans :\n{config.VCF_EXPORT_DIR}",
            parent=self,
        )


def run() -> None:
    """Point d'entrée de l'interface graphique."""
    config.ensure_dirs()
    db = ContactDatabase(config.DATABASE_PATH)
    try:
        app = App(db)
        app.mainloop()
    finally:
        db.close()
