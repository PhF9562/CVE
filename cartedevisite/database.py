"""Stockage local des contacts dans une base SQLite.

La base est créée automatiquement au premier usage. Le chemin par défaut se
trouve dans le dossier de données de l'application (``config.DATA_DIR``).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional, Union

from .models import Contact

# Colonnes persistées (l'ordre est utilisé pour le mapping ligne <-> contact).
_FIELDS = (
    "name", "company", "title", "phone", "email",
    "website", "address", "notes", "raw_text",
)


class ContactDatabase:
    """Couche d'accès aux contacts (SQLite)."""

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    # -- Cycle de vie -------------------------------------------------------

    def _create_schema(self) -> None:
        columns = ",\n".join(f"{field} TEXT NOT NULL DEFAULT ''" for field in _FIELDS)
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {columns},
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
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

    # -- Opérations CRUD ----------------------------------------------------

    def add(self, contact: Contact) -> int:
        """Insère un contact et retourne son identifiant."""
        placeholders = ", ".join("?" for _ in _FIELDS)
        cols = ", ".join(_FIELDS)
        cur = self._conn.execute(
            f"INSERT INTO contacts ({cols}) VALUES ({placeholders})",
            tuple(getattr(contact, f) for f in _FIELDS),
        )
        self._conn.commit()
        contact.id = int(cur.lastrowid)
        return contact.id

    def update(self, contact: Contact) -> None:
        """Met à jour un contact existant (``contact.id`` requis)."""
        if contact.id is None:
            raise ValueError("Impossible de mettre à jour un contact sans id.")
        assignments = ", ".join(f"{f} = ?" for f in _FIELDS)
        self._conn.execute(
            f"UPDATE contacts SET {assignments}, updated_at = datetime('now') WHERE id = ?",
            (*[getattr(contact, f) for f in _FIELDS], contact.id),
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

    def all(self) -> list[Contact]:
        rows = self._conn.execute(
            "SELECT * FROM contacts ORDER BY name COLLATE NOCASE, id"
        ).fetchall()
        return [self._row_to_contact(r) for r in rows]

    def search(self, term: str) -> list[Contact]:
        """Recherche plein texte simple sur les champs principaux."""
        like = f"%{term}%"
        rows = self._conn.execute(
            """
            SELECT * FROM contacts
            WHERE name LIKE ? OR company LIKE ? OR email LIKE ? OR phone LIKE ?
            ORDER BY name COLLATE NOCASE, id
            """,
            (like, like, like, like),
        ).fetchall()
        return [self._row_to_contact(r) for r in rows]

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0])

    def add_many(self, contacts: Iterable[Contact]) -> list[int]:
        return [self.add(c) for c in contacts]

    # -- Helpers ------------------------------------------------------------

    @staticmethod
    def _row_to_contact(row: sqlite3.Row) -> Contact:
        data = {f: row[f] for f in _FIELDS}
        data["id"] = row["id"]
        return Contact.from_dict(data)
