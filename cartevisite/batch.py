"""Traitement par lots d'un dossier de scans de cartes de visite.

Organisation des dossiers attendue (par défaut sous ``OneDrive/numérisation``) ::

    numérisation/
    ├── CV-Scan/   ← scans à analyser (JPG, PNG, PDF, TIFF… ou .txt)
    ├── CV-VCF/    ← fichiers vCard (.vcf) générés, un par contact
    └── CV-JSON/   ← données extraites au format JSON

La fonction :func:`process_directory` parcourt ``CV-Scan``, applique l'OCR
et l'analyse à chaque fichier, puis écrit les résultats dans ``CV-VCF`` et
``CV-JSON``. Elle est tolérante aux erreurs : un scan illisible n'interrompt
pas le lot, il est simplement signalé dans le rapport.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from .export import JSON_DIR, VCF_DIR, export_json, export_vcards
from .models import Contact
from .ocr import SUPPORTED_SUFFIXES, extract_text
from .parser import parse_contact

SCAN_DIR = "CV-Scan"
PROCESSED_DIR = "traités"  # sous-dossier de CV-Scan pour les scans déjà traités


@dataclass
class BatchResult:
    """Rapport d'un traitement par lots."""

    base_dir: Path
    contacts: List[Contact] = field(default_factory=list)
    processed_files: List[str] = field(default_factory=list)
    failures: List[tuple] = field(default_factory=list)  # (fichier, message)
    json_path: Optional[Path] = None
    vcf_paths: List[Path] = field(default_factory=list)
    moved_files: List[Path] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Dossier        : {self.base_dir}",
            f"Scans traités  : {len(self.processed_files)}",
            f"Contacts       : {len(self.contacts)}",
            f"Échecs         : {len(self.failures)}",
        ]
        if self.json_path:
            lines.append(f"JSON           : {self.json_path}")
        if self.vcf_paths:
            lines.append(f"vCard          : {len(self.vcf_paths)} fichier(s) dans {VCF_DIR}/")
        if self.moved_files:
            lines.append(
                f"Déplacés       : {len(self.moved_files)} scan(s) vers "
                f"{SCAN_DIR}/{PROCESSED_DIR}/"
            )
        for name, msg in self.failures:
            lines.append(f"  ⚠ {name} : {msg}")
        return "\n".join(lines)


def find_base_dir(explicit: Optional[Union[str, Path]] = None) -> Path:
    """Détermine le dossier de travail ``numérisation``.

    Ordre de résolution :

    1. le chemin ``explicit`` fourni ;
    2. la variable d'environnement ``CV_BASE_DIR`` ;
    3. ``<OneDrive>/numérisation`` si un dossier OneDrive est détecté ;
    4. ``./numérisation`` dans le répertoire courant.
    """
    if explicit:
        return Path(explicit).expanduser()

    env = os.environ.get("CV_BASE_DIR")
    if env:
        return Path(env).expanduser()

    # Détection d'un dossier OneDrive courant (Windows/macOS/Linux).
    onedrive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
    candidates = []
    if onedrive:
        candidates.append(Path(onedrive))
    home = Path.home()
    candidates += [home / "OneDrive", home / "OneDrive - Personnel"]
    for od in candidates:
        target = od / "numérisation"
        if target.is_dir():
            return target

    return Path.cwd() / "numérisation"


def ensure_layout(base_dir: Path) -> None:
    """Crée les sous-dossiers ``CV-Scan``, ``CV-VCF`` et ``CV-JSON`` au besoin."""
    for sub in (SCAN_DIR, VCF_DIR, JSON_DIR):
        (base_dir / sub).mkdir(parents=True, exist_ok=True)


def list_scans(base_dir: Path) -> List[Path]:
    """Renvoie les fichiers de ``CV-Scan`` exploitables, triés par nom.

    Le sous-dossier ``traités`` est ignoré : ``iterdir`` ne parcourt pas la
    récursion et ``is_file()`` écarte les dossiers.
    """
    scan_dir = base_dir / SCAN_DIR
    if not scan_dir.is_dir():
        return []
    files = [
        p for p in scan_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    return sorted(files, key=lambda p: p.name.lower())


def _move_to_processed(path: Path, processed_dir: Path) -> Path:
    """Déplace un scan vers ``processed_dir`` en évitant les collisions de nom."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    target = processed_dir / path.name
    if target.exists():
        suffix = 1
        while True:
            suffix += 1
            candidate = processed_dir / f"{path.stem}_{suffix}{path.suffix}"
            if not candidate.exists():
                target = candidate
                break
    return Path(path.replace(target))


def process_directory(
    base_dir: Optional[Union[str, Path]] = None,
    lang: str = "fra+eng",
    db_path: Optional[Union[str, Path]] = None,
    move_processed: bool = True,
    log=print,
) -> BatchResult:
    """Analyse tous les scans de ``CV-Scan`` et exporte JSON + vCard.

    :param base_dir:       dossier ``numérisation`` (auto-détecté si ``None``).
    :param lang:           langues Tesseract (ex. ``"fra+eng"``).
    :param db_path:        si fourni, les contacts sont aussi enregistrés en base.
    :param move_processed: déplacer les scans traités avec succès vers
                           ``CV-Scan/traités`` (évite de les ré-analyser).
    :param log:            fonction d'affichage de la progression.
    :returns:              un :class:`BatchResult` détaillant le traitement.
    """
    base = find_base_dir(base_dir)
    ensure_layout(base)
    result = BatchResult(base_dir=base)

    scans = list_scans(base)
    if not scans:
        log(f"Aucun scan exploitable dans {base / SCAN_DIR}.")
        return result

    succeeded: List[Path] = []  # scans dont l'extraction a réussi (à déplacer)
    log(f"{len(scans)} scan(s) à traiter dans {base / SCAN_DIR}…")
    for path in scans:
        try:
            text = extract_text(path, lang=lang)
            contact = parse_contact(text)
            if contact.is_empty():
                result.failures.append((path.name, "aucune information détectée"))
                log(f"  ⚠ {path.name} : aucune information détectée")
                continue
            result.contacts.append(contact)
            result.processed_files.append(path.name)
            succeeded.append(path)
            log(f"  ✓ {path.name} → {contact.display_label()}")
        except Exception as exc:  # un scan défaillant n'arrête pas le lot
            result.failures.append((path.name, str(exc)))
            log(f"  ⚠ {path.name} : {exc}")

    if not result.contacts:
        log("Aucun contact extrait : rien à exporter.")
        return result

    # Stockage optionnel en base locale. Lorsqu'une base est utilisée, les
    # exports portent sur TOUT le carnet d'adresses (et non sur le seul lot
    # courant) : les scans étant archivés dans « traités », contacts.json
    # resterait sinon réduit au dernier lot et perdrait les contacts des
    # passages précédents.
    export_source = result.contacts
    if db_path is not None:
        from .database import ContactDatabase

        with ContactDatabase(db_path) as db:
            for contact in result.contacts:
                db.add(contact)
            export_source = db.all()

    # Exports dans CV-JSON et CV-VCF.
    result.json_path = export_json(export_source, base)
    result.vcf_paths = export_vcards(export_source, base)
    log(
        f"Export terminé : {result.json_path} et "
        f"{len(result.vcf_paths)} fichier(s) vCard dans {base / VCF_DIR}."
    )

    # Archivage des scans traités avec succès (seulement après export réussi).
    if move_processed and succeeded:
        processed_dir = base / SCAN_DIR / PROCESSED_DIR
        for path in succeeded:
            try:
                moved = _move_to_processed(path, processed_dir)
                result.moved_files.append(moved)
            except OSError as exc:  # déplacement impossible : on signale sans bloquer
                log(f"  ⚠ déplacement de {path.name} impossible : {exc}")
        log(
            f"{len(result.moved_files)} scan(s) déplacé(s) vers "
            f"{processed_dir}."
        )

    return result
