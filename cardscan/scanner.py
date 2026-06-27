"""Balayage de répertoires pour découvrir et analyser des cartes en lot.

Plutôt que d'importer les cartes une par une, l'utilisateur peut pointer un
dossier : le scanner parcourt l'arborescence, repère tous les fichiers
exploitables (images et PDF) et lance l'OCR sur chacun.

La *découverte* des fichiers (:func:`find_card_files`) ne dépend que de la
bibliothèque standard et reste donc testable sans OpenCV ni Tesseract.
L'*analyse* (:func:`scan_directory`) s'appuie sur :mod:`cardscan.ocr`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Union

from .contact import Contact

# Extensions de fichiers considérées comme des cartes de visite.
SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".pdf",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
    ".gif",
}


def is_supported(path: Union[str, Path]) -> bool:
    """Vrai si le fichier a une extension prise en charge."""
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def find_card_files(
    directory: Union[str, Path], recursive: bool = True
) -> List[Path]:
    """Liste les fichiers analysables d'un répertoire.

    :param directory: dossier à balayer.
    :param recursive: parcourir aussi les sous-dossiers (par défaut : oui).
    :returns: chemins triés, dédoublonnés, des fichiers pris en charge.
    :raises NotADirectoryError: si ``directory`` n'est pas un dossier.
    """
    root = Path(directory)
    if not root.is_dir():
        raise NotADirectoryError(f"{root} n'est pas un répertoire.")

    iterator = root.rglob("*") if recursive else root.glob("*")
    files = {
        p.resolve()
        for p in iterator
        if p.is_file() and is_supported(p)
    }
    return sorted(files)


@dataclass
class ScanResult:
    """Résultat de l'analyse d'un fichier lors d'un balayage."""

    path: Path
    contact: Optional[Contact] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


def scan_directory(
    directory: Union[str, Path],
    recursive: bool = True,
    lang: str = "fra+eng",
    progress: Optional[Callable[[int, int, Path], None]] = None,
) -> List[ScanResult]:
    """Balaye un répertoire et analyse chaque carte trouvée.

    Les erreurs sont capturées fichier par fichier : un fichier illisible ne
    fait pas échouer tout le lot, son :class:`ScanResult` porte le message
    d'erreur.

    :param progress: callback optionnel ``(index, total, chemin)`` appelé avant
        l'analyse de chaque fichier (utile pour une barre de progression).
    """
    # Import paresseux : on ne charge l'OCR (et ses dépendances) qu'ici.
    from .ocr import scan_card

    files = find_card_files(directory, recursive=recursive)
    total = len(files)
    results: List[ScanResult] = []
    for index, path in enumerate(files, start=1):
        if progress is not None:
            progress(index, total, path)
        try:
            contact = scan_card(path, lang=lang)
            results.append(ScanResult(path=path, contact=contact))
        except Exception as exc:  # noqa: BLE001 - on isole chaque fichier
            results.append(ScanResult(path=path, error=str(exc)))
    return results


def iter_scan_directory(
    directory: Union[str, Path],
    recursive: bool = True,
    lang: str = "fra+eng",
) -> Iterator[ScanResult]:
    """Variante générateur : renvoie les résultats au fil de l'eau.

    Pratique pour afficher chaque contact dès qu'il est analysé sans attendre
    la fin du lot.
    """
    from .ocr import scan_card

    for path in find_card_files(directory, recursive=recursive):
        try:
            yield ScanResult(path=path, contact=scan_card(path, lang=lang))
        except Exception as exc:  # noqa: BLE001
            yield ScanResult(path=path, error=str(exc))
