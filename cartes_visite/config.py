"""Gestion du répertoire de travail et des emplacements de fichiers.

Toutes les données de l'application (base de contacts, exports JSON/vCard,
captures photo) sont rangées sous un même **répertoire de travail**.

Par défaut, ce répertoire est détecté automatiquement : si **OneDrive** est
présent sur la machine, les données vont dans ``<OneDrive>/CartesDeVisite`` (donc
sauvegardées et synchronisées dans le cloud) ; sinon dans
``<dossier personnel>/CartesDeVisite``. L'utilisateur peut toujours imposer un
autre dossier (option ``--data-dir`` ou bouton de l'interface), choix qui est
alors mémorisé d'une session à l'autre.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import exporter

# Noms des fichiers/dossiers créés sous le répertoire de travail.
NOM_DB = "contacts.db"
NOM_CAPTURE = "capture_carte.png"

# Sous-dossier créé dans OneDrive (ou ailleurs) pour ranger les données.
NOM_SOUS_DOSSIER = "CartesDeVisite"

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


def detecter_onedrive() -> Path | None:
    """Tente de localiser le dossier OneDrive de l'utilisateur.

    Ordre de recherche :

    1. les variables d'environnement posées par OneDrive sous Windows
       (``OneDrive``, ``OneDriveConsumer``, ``OneDriveCommercial``) ;
    2. ``~/OneDrive`` (Windows/Linux) ;
    3. ``~/Library/CloudStorage/OneDrive-*`` (macOS, client récent).

    Retourne le premier dossier existant, ou ``None`` si OneDrive est introuvable.
    """
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        valeur = os.environ.get(var)
        if valeur and Path(valeur).is_dir():
            return Path(valeur)

    accueil = Path.home()
    candidats: list[Path] = [accueil / "OneDrive"]

    cloud = accueil / "Library" / "CloudStorage"
    if cloud.is_dir():
        # ex. OneDrive-Personal, OneDrive-Entreprise…
        candidats.extend(sorted(cloud.glob("OneDrive*")))

    for candidat in candidats:
        if candidat.is_dir():
            return candidat
    return None


def repertoire_par_defaut() -> Path:
    """Répertoire de travail par défaut.

    Si OneDrive est détecté, les données sont rangées dans
    ``<OneDrive>/CartesDeVisite`` (sauvegardé et synchronisé dans le cloud).
    Sinon, on retombe sur ``<dossier personnel>/CartesDeVisite``.
    """
    base = detecter_onedrive() or Path.home()
    return base / NOM_SOUS_DOSSIER


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
    (si ``utiliser_config``) > répertoire par défaut (OneDrive si détecté).
    Le dossier est créé au passage.
    """
    base: str | Path
    if repertoire is not None:
        base = repertoire
    elif utiliser_config and (memorise := charger_repertoire_enregistre()):
        base = memorise
    else:
        base = repertoire_par_defaut()
    return EmplacementDonnees(base).creer()
