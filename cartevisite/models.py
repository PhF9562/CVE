"""Modèle de données représentant un contact extrait d'une carte de visite."""

from __future__ import annotations

from dataclasses import dataclass, asdict, fields
from typing import Any, Dict, Optional


@dataclass
class Contact:
    """Un contact issu d'une carte de visite.

    Tous les champs sont optionnels : l'OCR ne parvient pas toujours à
    reconnaître l'intégralité des informations, et l'utilisateur peut
    compléter ou corriger les valeurs manuellement avant la sauvegarde.
    """

    full_name: str = ""
    company: str = ""
    title: str = ""          # poste / fonction
    phone: str = ""
    email: str = ""
    website: str = ""
    address: str = ""
    notes: str = ""
    raw_text: str = ""       # texte brut renvoyé par l'OCR
    id: Optional[int] = None  # identifiant en base, None tant que non sauvegardé

    # -- Sérialisation ---------------------------------------------------

    def to_dict(self, include_id: bool = True) -> Dict[str, Any]:
        """Renvoie le contact sous forme de dictionnaire.

        :param include_id: inclure l'identifiant de base de données.
        """
        data = asdict(self)
        if not include_id:
            data.pop("id", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Contact":
        """Construit un :class:`Contact` à partir d'un dictionnaire.

        Les clés inconnues sont ignorées, ce qui rend le chargement
        tolérant à d'éventuelles évolutions du schéma.
        """
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    # -- Confort ---------------------------------------------------------

    def is_empty(self) -> bool:
        """Vrai si aucune information exploitable n'a été renseignée."""
        meaningful = (
            self.full_name,
            self.company,
            self.title,
            self.phone,
            self.email,
            self.website,
            self.address,
        )
        return not any(value.strip() for value in meaningful)

    def display_label(self) -> str:
        """Libellé court pour l'affichage dans une liste de contacts."""
        for value in (self.full_name, self.company, self.email, self.phone):
            if value.strip():
                return value.strip()
        return "(contact sans nom)"
