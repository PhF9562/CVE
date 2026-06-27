"""Gestion du répertoire de travail et des emplacements de fichiers.

Toutes les données de l'application (base de contacts, exports JSON/vCard,
captures photo) sont rangées sous un même **répertoire de travail** choisi par
l'utilisateur. Ce module résout les chemins à partir de ce répertoire et permet
de mémoriser le dernier dossier utilisé d'une session à l'autre.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import exporter

# Noms des fichiers/dossiers créés sous le répertoire de travail.
NOM_DB = "contacts.db"
NOM_CAPTURE = "capture_carte.png"

# Fichier de configuration mémorisant le dernier répertoire de travail.
FICHIER_CONFIG = Path.home() / ".cartes_visite.json"


class EmplacementDonnees:
    """Résout les chemins des données à partir d'un répertoire de travail.

    >>> emp = EmplacementDonnees("~/mes_cartes")
    >>> emp.chemin_db.name
    'contacts.db'
    """

    def __init__(self, base: str | Path = ".") -> None:
        self.base = Path(base).expanduser()

    @property
    def chemin_db(self) -> Path:
        return self.base / NOM_DB

    @property
    def dossier_json(self) -> Path:
        return self.base / exporter.DOSSIER_JSON

    @property
    def dossier_vcf(self) -> Path:
        return self.base / exporter.DOSSIER_VCF

    @property
    def chemin_capture(self) -> Path:
        return self.base / NOM_CAPTURE

    def creer(self) -> "EmplacementDonnees":
        """Crée le répertoire de travail s'il n'existe pas, puis se retourne."""
        self.base.mkdir(parents=True, exist_ok=True)
        return self

    def __str__(self) -> str:
        return str(self.base)


def charger_repertoire_enregistre(defaut: str | None = None) -> str | None:
    """Retourne le dernier répertoire de travail mémorisé, ou ``defaut``."""
    try:
        donnees = json.loads(FICHIER_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaut
    rep = donnees.get("repertoire_travail")
    return rep if rep else defaut


def enregistrer_repertoire(chemin: str | Path) -> bool:
    """Mémorise le répertoire de travail. Retourne True en cas de succès."""
    try:
        FICHIER_CONFIG.write_text(
            json.dumps({"repertoire_travail": str(chemin)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def resoudre_emplacement(
    repertoire: str | Path | None = None,
    *,
    utiliser_config: bool = True,
) -> EmplacementDonnees:
    """Détermine le répertoire de travail à utiliser.

    Priorité : argument explicite ``repertoire`` > dernier dossier mémorisé
    (si ``utiliser_config``) > répertoire courant. Le dossier est créé au passage.
    """
    base: str | Path
    if repertoire is not None:
        base = repertoire
    elif utiliser_config:
        base = charger_repertoire_enregistre(defaut=".") or "."
    else:
        base = "."
    return EmplacementDonnees(base).creer()
