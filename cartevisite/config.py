"""Préférences persistantes de l'application.

Stocke le dossier de travail choisi par l'utilisateur (le dossier
``numérisation`` contenant ``CV-Scan``/``CV-VCF``/``CV-JSON``) afin qu'il
n'ait à le sélectionner qu'une seule fois, au premier lancement.

Le fichier de configuration est un simple JSON situé par défaut dans
``~/.cartevisite/config.json``. Son emplacement peut être redéfini via la
variable d'environnement ``CARTEVISITE_CONFIG`` (utile pour les tests).

Ce module ne dépend d'aucune bibliothèque externe et reste testable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

APP_DIR_NAME = ".cartevisite"
CONFIG_FILENAME = "config.json"


def config_path() -> Path:
    """Chemin du fichier de configuration (créé à la demande)."""
    override = os.environ.get("CARTEVISITE_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / APP_DIR_NAME / CONFIG_FILENAME


def app_dir() -> Path:
    """Dossier applicatif (où vit la configuration), créé au besoin.

    Sert d'emplacement de repli stable pour la base et les exports tant
    qu'aucun dossier de travail n'a été choisi — évite de semer des
    fichiers dans un répertoire courant arbitraire.
    """
    directory = config_path().parent
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def load_config() -> Dict[str, Any]:
    """Charge la configuration. Renvoie ``{}`` si absente ou illisible."""
    path = config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(config: Dict[str, Any]) -> Path:
    """Écrit la configuration sur le disque et renvoie son chemin."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def get_base_dir() -> Optional[Path]:
    """Renvoie le dossier de travail mémorisé, ou ``None`` s'il n'y en a pas.

    Une valeur absente, vide ou non textuelle (config corrompue ou éditée à
    la main) est traitée comme « non défini » plutôt que de propager une
    erreur.
    """
    value = load_config().get("base_dir")
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value).expanduser()


def set_base_dir(path) -> Path:
    """Mémorise ``path`` comme dossier de travail. Renvoie le chemin du config.

    Le chemin est développé (``~``) et rendu absolu afin qu'il reste valide
    quel que soit le répertoire courant au prochain lancement.
    """
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = resolved.absolute()
    config = load_config()
    config["base_dir"] = str(resolved)
    return save_config(config)
