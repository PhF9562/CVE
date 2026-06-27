"""Emplacements de fichiers et constantes de configuration de l'application."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "CarteDeVisite"


def _base_dir() -> Path:
    """Dossier de données de l'application, dépendant du système.

    Surchargé par la variable d'environnement ``CARTEDEVISITE_HOME`` si définie
    (pratique pour les tests et les usages portables).
    """
    override = os.environ.get("CARTEDEVISITE_HOME")
    if override:
        return Path(override).expanduser()

    home = Path.home()
    if os.name == "nt":  # Windows
        root = Path(os.environ.get("APPDATA", home))
    elif "XDG_DATA_HOME" in os.environ:  # Linux/BSD
        root = Path(os.environ["XDG_DATA_HOME"])
    else:
        root = home / ".local" / "share"
    return root / APP_NAME


DATA_DIR = _base_dir()
DATABASE_PATH = DATA_DIR / "contacts.db"

# Dossiers d'export imposés par le cahier des charges.
JSON_EXPORT_DIR = DATA_DIR / "CV-JSON"
VCF_EXPORT_DIR = DATA_DIR / "CV-VCF"

# Extensions acceptées à l'import.
SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif")
SUPPORTED_DOCUMENT_EXTENSIONS = (".pdf",)
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS + SUPPORTED_DOCUMENT_EXTENSIONS

# Langues passées à Tesseract (français + anglais par défaut).
OCR_LANGUAGES = os.environ.get("CARTEDEVISITE_OCR_LANG", "fra+eng")


def ensure_dirs() -> None:
    """Crée les dossiers de données et d'export s'ils n'existent pas."""
    for directory in (DATA_DIR, JSON_EXPORT_DIR, VCF_EXPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
