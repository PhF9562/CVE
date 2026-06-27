"""Modèle de données représentant un contact issu d'une carte de visite."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Optional


@dataclass
class Contact:
    """Informations extraites d'une carte de visite.

    Tous les champs sont optionnels : l'OCR ne parvient pas toujours à
    reconnaître chaque information, et l'utilisateur peut compléter ou
    corriger les valeurs manuellement avant la sauvegarde.
    """

    nom: str = ""
    entreprise: str = ""
    poste: str = ""
    telephone: str = ""
    email: str = ""
    site_web: str = ""
    adresse: str = ""
    notes: str = ""
    id: Optional[int] = field(default=None)

    def to_dict(self) -> dict:
        """Retourne le contact sous forme de dictionnaire (champs non vides triés)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Contact":
        """Construit un contact à partir d'un dictionnaire en ignorant les clés inconnues."""
        champs = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in champs and v is not None})

    def est_vide(self) -> bool:
        """Indique si aucune information exploitable n'a été renseignée."""
        return not any(
            getattr(self, champ)
            for champ in (
                "nom",
                "entreprise",
                "poste",
                "telephone",
                "email",
                "site_web",
                "adresse",
            )
        )

    def libelle(self) -> str:
        """Libellé court pour l'affichage dans une liste."""
        principal = self.nom or self.email or self.entreprise or "(sans nom)"
        if self.entreprise and self.entreprise != principal:
            return f"{principal} — {self.entreprise}"
        return principal
