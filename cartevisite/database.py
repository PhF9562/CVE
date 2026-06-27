"""Stockage local des contacts dans une base SQLite.

La classe :class:`ContactDatabase` encapsule toutes les opérations CRUD.
Elle crée automatiquement le schéma à l'ouverture et peut fonctionner
entièrement en mémoire (``":memory:"``) pour les tests.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional, Union

from .models import Contact

# Colonnes persistées (l'identifiant est géré séparément en clé primaire).
_COLUMNS = (
    "full_name",
    "company",
    "title",
    "phone",
    "email",
    "website",
    "address",
    "notes",
    "raw_text",
)

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS contacts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    {", ".join(f"{col} TEXT NOT NULL DEFAULT ''" for col in _COLUMNS)},
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class ContactDatabase:
    """Accès à la base de contacts.

    Utilisable comme gestionnaire de contexte ::

        with ContactDatabase("contacts.db") as db:
            db.add(contact)
    """

    def __init__(self, path: Union[str, Path] = "contacts.db") -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        # Le traitement par lots (interface) ouvre une seconde connexion dans
        # un thread de travail ; un délai d'attente évite une erreur immédiate
        # « database is locked » si une lecture survient pendant une écriture.
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- Gestionnaire de contexte ---------------------------------------

    def __enter__(self) -> "ContactDatabase":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    # -- Opérations CRUD -------------------------------------------------

    def add(self, contact: Contact) -> int:
        """Insère un contact et renvoie son nouvel identifiant."""
        placeholders = ", ".join("?" for _ in _COLUMNS)
        columns = ", ".join(_COLUMNS)
        values = [getattr(contact, col) for col in _COLUMNS]
        cur = self._conn.execute(
            f"INSERT INTO contacts ({columns}) VALUES ({placeholders})",
            values,
        )
        self._conn.commit()
        contact.id = int(cur.lastrowid)
        return contact.id

    def update(self, contact: Contact) -> bool:
        """Met à jour un contact existant. Renvoie ``True`` si une ligne a changé."""
        if contact.id is None:
            raise ValueError("Le contact doit posséder un identifiant pour être mis à jour.")
        assignments = ", ".join(f"{col} = ?" for col in _COLUMNS)
        values = [getattr(contact, col) for col in _COLUMNS]
        values.append(contact.id)
        cur = self._conn.execute(
            f"UPDATE contacts SET {assignments} WHERE id = ?",
            values,
        )
        self._conn.commit()
        return cur.rowcount > 0

    def delete(self, contact_id: int) -> bool:
        """Supprime un contact par identifiant."""
        cur = self._conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def get(self, contact_id: int) -> Optional[Contact]:
        row = self._conn.execute(
            "SELECT * FROM contacts WHERE id = ?", (contact_id,)
        ).fetchone()
        return self._row_to_contact(row) if row else None

    def all(self) -> List[Contact]:
        """Renvoie tous les contacts, triés par nom puis par identifiant."""
        rows = self._conn.execute(
            "SELECT * FROM contacts ORDER BY full_name COLLATE NOCASE, id"
        ).fetchall()
        return [self._row_to_contact(row) for row in rows]

    def search(self, term: str) -> List[Contact]:
        """Recherche plein-texte simple sur les principaux champs."""
        like = f"%{term}%"
        rows = self._conn.execute(
            """
            SELECT * FROM contacts
            WHERE full_name LIKE ? OR company LIKE ? OR email LIKE ?
               OR phone LIKE ? OR title LIKE ?
            ORDER BY full_name COLLATE NOCASE, id
            """,
            (like, like, like, like, like),
        ).fetchall()
        return [self._row_to_contact(row) for row in rows]

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0])

    # -- Utilitaires -----------------------------------------------------

    @staticmethod
    def _row_to_contact(row: sqlite3.Row) -> Contact:
        return Contact(
            id=row["id"],
            full_name=row["full_name"],
            company=row["company"],
            title=row["title"],
            phone=row["phone"],
            email=row["email"],
            website=row["website"],
            address=row["address"],
            notes=row["notes"],
            raw_text=row["raw_text"],
        )
