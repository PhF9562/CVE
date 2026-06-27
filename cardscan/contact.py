"""Modèle de données pour un contact (carte de visite)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, Optional


@dataclass
class Contact:
    """Représente une carte de visite numérisée.

    Tous les champs sont optionnels : l'OCR ne parvient pas toujours à
    extraire l'intégralité des informations, et l'utilisateur peut compléter
    ou corriger les valeurs manuellement avant la sauvegarde.
    """

    full_name: str = ""
    company: str = ""
    job_title: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    address: str = ""
    notes: str = ""
    # Renseigné par la base de données une fois le contact enregistré.
    id: Optional[int] = field(default=None)

    # ------------------------------------------------------------------
    # Sérialisation
    # ------------------------------------------------------------------
    def to_dict(self, include_id: bool = True) -> Dict[str, Any]:
        """Retourne le contact sous forme de dictionnaire.

        :param include_id: inclure (ou non) l'identifiant de base de données.
        """
        data = asdict(self)
        if not include_id:
            data.pop("id", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Contact":
        """Construit un :class:`Contact` à partir d'un dictionnaire.

        Les clés inconnues sont ignorées afin de tolérer les fichiers
        d'import provenant de sources variées.
        """
        known = {f.name for f in fields(cls)}
        cleaned = {k: v for k, v in data.items() if k in known and v is not None}
        return cls(**cleaned)

    def is_empty(self) -> bool:
        """Vrai si aucune information exploitable n'a été renseignée."""
        return not any(
            getattr(self, f.name)
            for f in fields(self)
            if f.name != "id"
        )

    def display_name(self) -> str:
        """Libellé lisible pour les listes de l'interface."""
        if self.full_name:
            return self.full_name
        if self.company:
            return self.company
        if self.email:
            return self.email
        return "(sans nom)"
