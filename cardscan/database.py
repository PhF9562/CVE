"""Stockage local des contacts dans une base SQLite.

La base est créée automatiquement au premier lancement dans le répertoire de
données de l'application (``~/.cardscan/contacts.db`` par défaut). Toutes les
opérations courantes (création, lecture, mise à jour, suppression, recherche)
sont exposées via la classe :class:`ContactDatabase`.

Ce module ne dépend que de la bibliothèque standard.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional, Union

from .contact import Contact

# Colonnes persistées (l'ordre est utilisé pour les requêtes INSERT/SELECT).
_COLUMNS = [
    "full_name",
    "company",
    "job_title",
    "email",
    "phone",
    "website",
    "address",
    "notes",
]


def default_db_path() -> Path:
    """Chemin par défaut de la base de données dans le dossier utilisateur."""
    base = Path.home() / ".cardscan"
    base.mkdir(parents=True, exist_ok=True)
    return base / "contacts.db"


class ContactDatabase:
    """Couche d'accès aux données pour les contacts.

    Peut être utilisée comme gestionnaire de contexte::

        with ContactDatabase() as db:
            db.add(contact)
    """

    def __init__(self, path: Union[str, Path, None] = None):
        # ``:memory:`` est pratique pour les tests.
        if path is None:
            path = default_db_path()
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._create_schema()

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------
    def _create_schema(self) -> None:
        columns_sql = ",\n            ".join(f"{c} TEXT NOT NULL DEFAULT ''" for c in _COLUMNS)
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {columns_sql},
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ContactDatabase":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def add(self, contact: Contact) -> int:
        """Insère un contact et renvoie son identifiant."""
        placeholders = ", ".join("?" for _ in _COLUMNS)
        cols = ", ".join(_COLUMNS)
        values = [getattr(contact, c) for c in _COLUMNS]
        cur = self._conn.execute(
            f"INSERT INTO contacts ({cols}) VALUES ({placeholders})", values
        )
        self._conn.commit()
        contact.id = cur.lastrowid
        return cur.lastrowid

    def update(self, contact: Contact) -> None:
        """Met à jour un contact existant (identifié par ``contact.id``)."""
        if contact.id is None:
            raise ValueError("Le contact n'a pas d'identifiant : utilisez add().")
        assignments = ", ".join(f"{c} = ?" for c in _COLUMNS)
        values = [getattr(contact, c) for c in _COLUMNS]
        values.append(contact.id)
        self._conn.execute(
            f"UPDATE contacts SET {assignments} WHERE id = ?", values
        )
        self._conn.commit()

    def delete(self, contact_id: int) -> None:
        self._conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        self._conn.commit()

    def get(self, contact_id: int) -> Optional[Contact]:
        row = self._conn.execute(
            "SELECT * FROM contacts WHERE id = ?", (contact_id,)
        ).fetchone()
        return self._row_to_contact(row) if row else None

    def all(self) -> List[Contact]:
        rows = self._conn.execute(
            "SELECT * FROM contacts ORDER BY full_name COLLATE NOCASE, id"
        ).fetchall()
        return [self._row_to_contact(r) for r in rows]

    def search(self, query: str) -> List[Contact]:
        """Recherche plein texte simple sur les champs principaux."""
        like = f"%{query}%"
        rows = self._conn.execute(
            """
            SELECT * FROM contacts
            WHERE full_name LIKE ? OR company LIKE ? OR email LIKE ?
               OR phone LIKE ? OR job_title LIKE ?
            ORDER BY full_name COLLATE NOCASE, id
            """,
            (like, like, like, like, like),
        ).fetchall()
        return [self._row_to_contact(r) for r in rows]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_contact(row: sqlite3.Row) -> Contact:
        contact = Contact(**{c: row[c] for c in _COLUMNS})
        contact.id = row["id"]
        return contact
