"""Prétraitement d'image et reconnaissance optique de caractères (OCR).

Le module isole les dépendances « lourdes » (OpenCV, Pillow, pytesseract,
pdf2image) derrière des imports paresseux : importer :mod:`cardscan.ocr` ne
déclenche aucune erreur même si ces bibliothèques sont absentes. L'erreur
n'est levée qu'au moment où l'on tente réellement de lire une image, avec un
message expliquant quelle dépendance installer.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from .contact import Contact
from .parser import parse_text


class OCRUnavailableError(RuntimeError):
    """Levée lorsqu'une dépendance OCR nécessaire n'est pas installée."""


def _require(module_name: str, pip_name: str):
    """Importe un module optionnel ou lève une erreur explicite."""
    try:
        return __import__(module_name)
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        raise OCRUnavailableError(
            f"La bibliothèque « {pip_name} » est requise pour cette opération. "
            f"Installez-la avec : pip install {pip_name}"
        ) from exc


def preprocess(image):
    """Améliore une image pour l'OCR : niveaux de gris, débruitage, seuillage.

    :param image: tableau NumPy (image BGR telle que renvoyée par OpenCV).
    :returns: image binarisée prête pour Tesseract.
    """
    cv2 = _require("cv2", "opencv-python")

    if image is None:
        raise ValueError("Image vide ou illisible.")

    # Conversion en niveaux de gris.
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Débruitage léger préservant les contours.
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    # Seuillage adaptatif : robuste aux éclairages inégaux d'une photo.
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15,
    )
    return binary


def _load_image(path: Path):
    """Charge une image (corrige l'orientation EXIF si Pillow est présent)."""
    cv2 = _require("cv2", "opencv-python")
    numpy = _require("numpy", "numpy")

    try:
        from PIL import Image, ImageOps

        with Image.open(path) as pil_img:
            pil_img = ImageOps.exif_transpose(pil_img)  # corrige l'orientation
            pil_img = pil_img.convert("RGB")
            rgb = numpy.array(pil_img)
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except ImportError:
        # Repli sans Pillow : pas de correction EXIF.
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Impossible de lire l'image : {path}")
        return image


def _pdf_to_images(path: Path):
    """Convertit chaque page d'un PDF en image OpenCV."""
    convert = _require("pdf2image", "pdf2image")
    numpy = _require("numpy", "numpy")
    cv2 = _require("cv2", "opencv-python")

    pages = convert.convert_from_path(str(path), dpi=300)
    images = []
    for page in pages:
        rgb = numpy.array(page.convert("RGB"))
        images.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return images


def image_to_text(image, lang: str = "fra+eng") -> str:
    """Lance Tesseract sur une image (déjà chargée) et renvoie le texte."""
    pytesseract = _require("pytesseract", "pytesseract")
    processed = preprocess(image)
    return pytesseract.image_to_string(processed, lang=lang)


def file_to_text(path: Union[str, Path], lang: str = "fra+eng") -> str:
    """Lit un fichier (image ou PDF) et renvoie le texte OCR concaténé."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() == ".pdf":
        images = _pdf_to_images(path)
    else:
        images = [_load_image(path)]

    texts: List[str] = [image_to_text(img, lang=lang) for img in images]
    return "\n".join(texts)


def scan_card(path: Union[str, Path], lang: str = "fra+eng") -> Contact:
    """Pipeline complet : fichier → OCR → contact analysé.

    C'est le point d'entrée utilisé par l'interface graphique lorsqu'une carte
    est importée ou photographiée.
    """
    text = file_to_text(path, lang=lang)
    return parse_text(text)
