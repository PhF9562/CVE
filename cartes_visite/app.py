"""Interface graphique (tkinter) de l'application de cartes de visite.

L'interface reste volontairement épurée : import d'un fichier (ou capture via la
caméra si OpenCV est disponible), écran de validation/édition des champs
détectés, liste des contacts et boutons d'export JSON / vCard.

Le traitement OCR s'exécute dans un thread d'arrière-plan afin de ne pas figer
l'interface.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path

from .contact import Contact
from .database import CarnetAdresses
from . import config, exporter, ocr
from .config import EmplacementDonnees

# tkinter fait partie de la bibliothèque standard mais peut être absent de
# certaines installations minimales : on diffère l'import vers le lancement.


class Application:
    """Fenêtre principale de l'application."""

    CHAMPS_EDITABLES = (
        ("nom", "Nom"),
        ("entreprise", "Entreprise"),
        ("poste", "Poste"),
        ("telephone", "Téléphone"),
        ("email", "E-mail"),
        ("site_web", "Site web"),
        ("adresse", "Adresse"),
        ("notes", "Notes"),
    )

    def __init__(self, emplacement: EmplacementDonnees | str | None = None) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk

        if not isinstance(emplacement, EmplacementDonnees):
            emplacement = config.resoudre_emplacement(emplacement)
        self.emplacement = emplacement.creer()

        self.carnet = CarnetAdresses(self.emplacement.chemin_db)
        self._file_resultats: "queue.Queue" = queue.Queue()
        self._contact_courant: Contact | None = None
        self._champ_vars: dict[str, "tk.StringVar"] = {}

        self.racine = tk.Tk()
        self.racine.title("Numérisation de cartes de visite")
        self.racine.geometry("760x560")
        self.racine.minsize(640, 480)

        self._construire_interface()
        self.rafraichir_liste()

    # -- Construction de l'interface ---------------------------------------
    def _construire_interface(self) -> None:
        tk, ttk = self.tk, self.ttk

        barre = ttk.Frame(self.racine, padding=10)
        barre.pack(fill="x")

        ttk.Button(
            barre, text="📷 Prendre une photo", command=self.prendre_photo
        ).pack(side="left", padx=4)
        ttk.Button(
            barre, text="📂 Importer un fichier", command=self.importer_fichier
        ).pack(side="left", padx=4)

        ttk.Separator(barre, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Button(
            barre, text="⬇ Exporter en JSON", command=self.exporter_json
        ).pack(side="left", padx=4)
        ttk.Button(
            barre, text="⬇ Exporter en vCard", command=self.exporter_vcard
        ).pack(side="left", padx=4)

        ttk.Button(
            barre, text="📁 Dossier de travail…", command=self.changer_repertoire
        ).pack(side="right", padx=4)

        # Ligne indiquant le répertoire de travail courant.
        self.var_repertoire = tk.StringVar()
        ttk.Label(
            self.racine, textvariable=self.var_repertoire, anchor="w",
            padding=(10, 0),
        ).pack(fill="x")
        self._maj_libelle_repertoire()

        self.var_statut = tk.StringVar(value="Prêt.")
        ttk.Label(
            self.racine, textvariable=self.var_statut, relief="sunken", anchor="w"
        ).pack(side="bottom", fill="x")

        corps = ttk.Frame(self.racine, padding=10)
        corps.pack(fill="both", expand=True)

        # --- Colonne gauche : liste des contacts ---------------------------
        gauche = ttk.Frame(corps)
        gauche.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ttk.Label(gauche, text="Carnet d'adresses").pack(anchor="w")
        self.liste = tk.Listbox(gauche, exportselection=False)
        self.liste.pack(fill="both", expand=True)
        self.liste.bind("<<ListboxSelect>>", self._sur_selection_liste)

        actions = ttk.Frame(gauche)
        actions.pack(fill="x", pady=4)
        ttk.Button(actions, text="Supprimer", command=self.supprimer_contact).pack(
            side="left"
        )

        # --- Colonne droite : édition du contact ---------------------------
        droite = ttk.LabelFrame(corps, text="Fiche contact", padding=10)
        droite.pack(side="right", fill="both", expand=True)

        for i, (champ, libelle) in enumerate(self.CHAMPS_EDITABLES):
            ttk.Label(droite, text=libelle).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            self._champ_vars[champ] = var
            ttk.Entry(droite, textvariable=var, width=40).grid(
                row=i, column=1, sticky="we", pady=2, padx=4
            )
        droite.columnconfigure(1, weight=1)

        boutons = ttk.Frame(droite)
        boutons.grid(row=len(self.CHAMPS_EDITABLES), column=0, columnspan=2, pady=8)
        ttk.Button(boutons, text="Nouveau", command=self.nouveau_contact).pack(
            side="left", padx=4
        )
        ttk.Button(boutons, text="💾 Enregistrer", command=self.enregistrer_contact).pack(
            side="left", padx=4
        )

    # -- Répertoire de travail ---------------------------------------------
    def _maj_libelle_repertoire(self) -> None:
        self.var_repertoire.set(f"Dossier de travail : {self.emplacement.base}")

    def changer_repertoire(self) -> None:
        """Demande un nouveau répertoire de travail, le mémorise et recharge."""
        from tkinter import filedialog

        choix = filedialog.askdirectory(
            title="Choisir le dossier de travail",
            initialdir=str(self.emplacement.base),
            mustexist=True,
        )
        if not choix:
            return

        # Bascule sur le nouvel emplacement.
        self.carnet.fermer()
        self.emplacement = EmplacementDonnees(choix).creer()
        self.carnet = CarnetAdresses(self.emplacement.chemin_db)
        config.enregistrer_repertoire(self.emplacement.base)

        self.nouveau_contact()
        self.rafraichir_liste()
        self._maj_libelle_repertoire()
        self.var_statut.set(f"Dossier de travail : {self.emplacement.base}")

    # -- Actions d'import / OCR --------------------------------------------
    def importer_fichier(self) -> None:
        from tkinter import filedialog

        chemin = filedialog.askopenfilename(
            title="Choisir une carte de visite",
            filetypes=[
                ("Images et PDF", " ".join(f"*{e}" for e in ocr.EXTENSIONS_SUPPORTEES)),
                ("Tous les fichiers", "*.*"),
            ],
        )
        if chemin:
            self._lancer_ocr(Path(chemin))

    def prendre_photo(self) -> None:
        """Capture une image depuis la webcam via OpenCV, puis lance l'OCR."""
        from tkinter import messagebox

        try:
            import cv2  # type: ignore
        except ImportError:
            messagebox.showwarning(
                "Caméra indisponible",
                "OpenCV (opencv-python) est requis pour la prise de photo.\n"
                "Vous pouvez utiliser « Importer un fichier » à la place.",
            )
            return

        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            messagebox.showerror("Caméra", "Impossible d'accéder à la caméra.")
            return

        self.var_statut.set("Appuyez sur ESPACE pour capturer, ÉCHAP pour annuler.")
        capture_path = None
        try:
            while True:
                ok, image = cam.read()
                if not ok:
                    break
                cv2.imshow("Capture — ESPACE: photo, ECHAP: annuler", image)
                touche = cv2.waitKey(1) & 0xFF
                if touche == 27:  # ÉCHAP
                    break
                if touche == 32:  # ESPACE
                    capture_path = self.emplacement.chemin_capture
                    cv2.imwrite(str(capture_path), image)
                    break
        finally:
            cam.release()
            cv2.destroyAllWindows()

        if capture_path:
            self._lancer_ocr(capture_path)
        else:
            self.var_statut.set("Capture annulée.")

    def _lancer_ocr(self, chemin: Path) -> None:
        from tkinter import messagebox

        manquant = ocr.verifier_dependances()
        if manquant:
            messagebox.showwarning(
                "OCR indisponible",
                "Les dépendances suivantes sont nécessaires :\n  - "
                + "\n  - ".join(manquant)
                + "\n\nInstallez-les puis réessayez.",
            )
            return

        self.var_statut.set(f"Analyse de « {chemin.name} » en cours…")

        def tache() -> None:
            try:
                contact = ocr.extraire_contact(chemin)
                self._file_resultats.put(("ok", contact))
            except Exception as exc:  # noqa: BLE001 - remonté à l'utilisateur
                self._file_resultats.put(("erreur", str(exc)))

        threading.Thread(target=tache, daemon=True).start()
        self.racine.after(100, self._verifier_resultats)

    def _verifier_resultats(self) -> None:
        from tkinter import messagebox

        try:
            statut, charge = self._file_resultats.get_nowait()
        except queue.Empty:
            self.racine.after(100, self._verifier_resultats)
            return

        if statut == "ok":
            self._contact_courant = charge
            self._remplir_formulaire(charge)
            self.var_statut.set(
                "Carte analysée. Vérifiez les informations puis enregistrez."
            )
        else:
            messagebox.showerror("Erreur d'analyse", str(charge))
            self.var_statut.set("Échec de l'analyse.")

    # -- Gestion du formulaire / contacts ----------------------------------
    def _remplir_formulaire(self, contact: Contact) -> None:
        for champ, _ in self.CHAMPS_EDITABLES:
            self._champ_vars[champ].set(getattr(contact, champ))

    def _lire_formulaire(self) -> Contact:
        contact = self._contact_courant or Contact()
        for champ, _ in self.CHAMPS_EDITABLES:
            setattr(contact, champ, self._champ_vars[champ].get().strip())
        return contact

    def nouveau_contact(self) -> None:
        self._contact_courant = Contact()
        self._remplir_formulaire(self._contact_courant)
        self.liste.selection_clear(0, "end")
        self.var_statut.set("Nouveau contact.")

    def enregistrer_contact(self) -> None:
        from tkinter import messagebox

        contact = self._lire_formulaire()
        if contact.est_vide():
            messagebox.showinfo("Contact vide", "Aucune information à enregistrer.")
            return

        # Détection de doublon par e-mail pour un nouveau contact.
        if contact.id is None and contact.email:
            existant = self.carnet.trouver_par_email(contact.email)
            if existant is not None:
                if not messagebox.askyesno(
                    "Doublon possible",
                    f"Un contact avec l'e-mail « {contact.email} » existe déjà "
                    f"(« {existant.libelle()} »).\n\nMettre à jour ce contact ?",
                ):
                    return
                contact.id = existant.id

        self.carnet.enregistrer(contact)
        self._contact_courant = contact
        self.rafraichir_liste()
        self.var_statut.set(f"Contact « {contact.libelle()} » enregistré.")

    def supprimer_contact(self) -> None:
        from tkinter import messagebox

        if self._contact_courant is None or self._contact_courant.id is None:
            return
        if messagebox.askyesno(
            "Supprimer", f"Supprimer « {self._contact_courant.libelle()} » ?"
        ):
            self.carnet.supprimer(self._contact_courant.id)
            self.nouveau_contact()
            self.rafraichir_liste()
            self.var_statut.set("Contact supprimé.")

    def rafraichir_liste(self) -> None:
        self._contacts = self.carnet.lister()
        self.liste.delete(0, "end")
        for contact in self._contacts:
            self.liste.insert("end", contact.libelle())

    def _sur_selection_liste(self, _event) -> None:
        selection = self.liste.curselection()
        if not selection:
            return
        contact = self._contacts[selection[0]]
        self._contact_courant = contact
        self._remplir_formulaire(contact)

    # -- Exports ------------------------------------------------------------
    def exporter_json(self) -> None:
        from tkinter import messagebox

        contacts = self.carnet.lister()
        if not contacts:
            messagebox.showinfo("Export", "Aucun contact à exporter.")
            return
        chemin = exporter.exporter_json(contacts, dossier=self.emplacement.dossier_json)
        messagebox.showinfo(
            "Export JSON", f"{len(contacts)} contact(s) exporté(s) dans :\n{chemin}"
        )
        self.var_statut.set(f"Export JSON : {chemin}")

    def exporter_vcard(self) -> None:
        from tkinter import messagebox

        contacts = self.carnet.lister()
        if not contacts:
            messagebox.showinfo("Export", "Aucun contact à exporter.")
            return
        chemins = exporter.exporter_vcards(contacts, dossier=self.emplacement.dossier_vcf)
        messagebox.showinfo(
            "Export vCard",
            f"{len(chemins)} fichier(s) .vcf créé(s) dans :\n{self.emplacement.dossier_vcf}",
        )
        self.var_statut.set(f"Export vCard : {len(chemins)} fichier(s).")

    # -- Boucle principale --------------------------------------------------
    def lancer(self) -> None:
        try:
            self.racine.mainloop()
        finally:
            self.carnet.fermer()


def lancer_application(emplacement: EmplacementDonnees | str | None = None) -> None:
    """Point d'entrée pratique pour démarrer l'interface graphique."""
    Application(emplacement).lancer()
