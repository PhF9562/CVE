"""Stockage local des contacts dans une base SQLite.

Le module n'utilise que ``sqlite3`` de la bibliothèque standard. La base est
créée automatiquement au premier usage.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from .contact import Contact

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL DEFAULT '',
    entreprise  TEXT NOT NULL DEFAULT '',
    poste       TEXT NOT NULL DEFAULT '',
    telephone   TEXT NOT NULL DEFAULT '',
    email       TEXT NOT NULL DEFAULT '',
    site_web    TEXT NOT NULL DEFAULT '',
    adresse     TEXT NOT NULL DEFAULT '',
    notes       TEXT NOT NULL DEFAULT '',
    cree_le     TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_CHAMPS = (
    "nom",
    "entreprise",
    "poste",
    "telephone",
    "email",
    "site_web",
    "adresse",
    "notes",
)


class CarnetAdresses:
    """Carnet d'adresses persistant adossé à SQLite.

    Peut être utilisé comme gestionnaire de contexte ::

        with CarnetAdresses("contacts.db") as carnet:
            carnet.ajouter(contact)
    """

    def __init__(self, chemin: str | Path = "contacts.db") -> None:
        self.chemin = str(chemin)
        self._conn = sqlite3.connect(self.chemin)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- Gestionnaire de contexte ------------------------------------------
    def __enter__(self) -> "CarnetAdresses":
        return self

    def __exit__(self, *exc) -> None:
        self.fermer()

    def fermer(self) -> None:
        self._conn.close()

    # -- Opérations CRUD ---------------------------------------------------
    def ajouter(self, contact: Contact) -> int:
        """Insère un contact et retourne son identifiant."""
        valeurs = [getattr(contact, champ) for champ in _CHAMPS]
        colonnes = ", ".join(_CHAMPS)
        marqueurs = ", ".join("?" for _ in _CHAMPS)
        cur = self._conn.execute(
            f"INSERT INTO contacts ({colonnes}) VALUES ({marqueurs})", valeurs
        )
        self._conn.commit()
        contact.id = cur.lastrowid
        return cur.lastrowid

    def modifier(self, contact: Contact) -> None:
        """Met à jour un contact existant (nécessite ``contact.id``)."""
        if contact.id is None:
            raise ValueError("Impossible de modifier un contact sans identifiant.")
        assignations = ", ".join(f"{champ} = ?" for champ in _CHAMPS)
        valeurs = [getattr(contact, champ) for champ in _CHAMPS]
        valeurs.append(contact.id)
        self._conn.execute(
            f"UPDATE contacts SET {assignations} WHERE id = ?", valeurs
        )
        self._conn.commit()

    def enregistrer(self, contact: Contact) -> int:
        """Insère ou met à jour selon que le contact possède déjà un id."""
        if contact.id is None:
            return self.ajouter(contact)
        self.modifier(contact)
        return contact.id

    def supprimer(self, contact_id: int) -> None:
        self._conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        self._conn.commit()

    def obtenir(self, contact_id: int) -> Optional[Contact]:
        ligne = self._conn.execute(
            "SELECT * FROM contacts WHERE id = ?", (contact_id,)
        ).fetchone()
        return self._vers_contact(ligne) if ligne else None

    def lister(self) -> List[Contact]:
        """Retourne tous les contacts triés par nom puis entreprise."""
        lignes = self._conn.execute(
            "SELECT * FROM contacts ORDER BY nom COLLATE NOCASE, entreprise COLLATE NOCASE"
        ).fetchall()
        return [self._vers_contact(l) for l in lignes]

    def rechercher(self, terme: str) -> List[Contact]:
        """Recherche plein-texte simple sur les principaux champs."""
        motif = f"%{terme}%"
        lignes = self._conn.execute(
            """
            SELECT * FROM contacts
            WHERE nom LIKE ? OR entreprise LIKE ? OR email LIKE ?
               OR telephone LIKE ? OR poste LIKE ?
            ORDER BY nom COLLATE NOCASE
            """,
            (motif, motif, motif, motif, motif),
        ).fetchall()
        return [self._vers_contact(l) for l in lignes]

    def nombre(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]

    # -- Utilitaires -------------------------------------------------------
    @staticmethod
    def _vers_contact(ligne: sqlite3.Row) -> Contact:
        return Contact(
            id=ligne["id"],
            nom=ligne["nom"],
            entreprise=ligne["entreprise"],
            poste=ligne["poste"],
            telephone=ligne["telephone"],
            email=ligne["email"],
            site_web=ligne["site_web"],
            adresse=ligne["adresse"],
            notes=ligne["notes"],
        )
