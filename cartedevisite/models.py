"""Modèle de données pour un contact extrait d'une carte de visite."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Optional


@dataclass
class Contact:
    """Représente un contact issu d'une carte de visite.

    Tous les champs sont optionnels sauf qu'au moins l'un d'entre eux doit
    être renseigné pour qu'un contact ait du sens. ``id`` est attribué par la
    base de données et reste ``None`` tant que le contact n'a pas été sauvé.
    """

    name: str = ""
    company: str = ""
    title: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    address: str = ""
    notes: str = ""
    raw_text: str = ""
    id: Optional[int] = None

    def to_dict(self, include_id: bool = True) -> dict[str, Any]:
        """Retourne le contact sous forme de dictionnaire sérialisable."""
        data = asdict(self)
        if not include_id:
            data.pop("id", None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Contact":
        """Construit un contact à partir d'un dictionnaire (clés inconnues ignorées)."""
        allowed = {f for f in cls.__dataclass_fields__}  # noqa: E1101
        return cls(**{k: v for k, v in data.items() if k in allowed})

    def is_empty(self) -> bool:
        """Vrai si aucun champ identifiant n'est renseigné."""
        return not any(
            getattr(self, f).strip()
            for f in ("name", "company", "title", "phone", "email", "website", "address")
        )

    def display_name(self) -> str:
        """Libellé lisible pour les listes (nom, sinon société, sinon e-mail)."""
        for candidate in (self.name, self.company, self.email, self.phone):
            if candidate.strip():
                return candidate.strip()
        return "(contact sans nom)"
