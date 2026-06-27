"""Prétraitement d'image et reconnaissance optique de caractères (OCR).

Ce module isole les dépendances « lourdes » (OpenCV, pytesseract,
Pillow, pdf2image). Elles sont importées paresseusement afin que le reste
de l'application reste utilisable même si elles ne sont pas installées :
on lève alors une :class:`OCRUnavailableError` explicite.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from .models import Contact
from .parser import parse_contact


class OCRUnavailableError(RuntimeError):
    """Levée lorsqu'une dépendance OCR requise est absente."""


def dependencies_status() -> dict:
    """Renvoie l'état d'installation des dépendances optionnelles."""
    status = {}
    for name in ("cv2", "numpy", "pytesseract", "PIL", "pdf2image"):
        try:
            __import__(name)
            status[name] = True
        except Exception:  # pragma: no cover - dépend de l'environnement
            status[name] = False
    return status


def _require(module: str, package: str):
    try:
        return __import__(module)
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        raise OCRUnavailableError(
            f"La bibliothèque « {package} » est requise pour l'OCR mais "
            f"n'est pas installée. Installez-la avec : pip install {package}"
        ) from exc


def preprocess_image(image):
    """Améliore une image pour l'OCR : niveaux de gris + binarisation.

    :param image: image OpenCV (tableau NumPy BGR ou niveaux de gris).
    :returns: image binarisée prête pour Tesseract.
    """
    cv2 = _require("cv2", "opencv-python")

    if image is None:
        raise ValueError("Image vide ou illisible.")

    # Conversion en niveaux de gris si nécessaire.
    if len(getattr(image, "shape", ())) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Réduction du bruit puis seuillage adaptatif (robuste à l'éclairage).
    gray = cv2.medianBlur(gray, 3)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 10,
    )
    return binary


def image_to_text(image_path: Union[str, Path], lang: str = "fra+eng") -> str:
    """Applique l'OCR sur un fichier image et renvoie le texte brut."""
    cv2 = _require("cv2", "opencv-python")
    pytesseract = _require("pytesseract", "pytesseract")

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Impossible de lire l'image : {image_path}")

    processed = preprocess_image(image)
    try:
        return pytesseract.image_to_string(processed, lang=lang)
    except Exception:
        # Repli sur la langue par défaut si « fra » n'est pas disponible.
        return pytesseract.image_to_string(processed)


def pdf_to_text(pdf_path: Union[str, Path], lang: str = "fra+eng") -> str:
    """Convertit chaque page d'un PDF en image puis applique l'OCR."""
    convert_from_path = getattr(
        _require("pdf2image", "pdf2image"), "convert_from_path"
    )
    pytesseract = _require("pytesseract", "pytesseract")
    np = _require("numpy", "numpy")
    cv2 = _require("cv2", "opencv-python")

    pages = convert_from_path(str(pdf_path))
    texts: List[str] = []
    for page in pages:
        # Pillow -> NumPy (RGB) -> OpenCV (BGR).
        array = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
        processed = preprocess_image(array)
        try:
            texts.append(pytesseract.image_to_string(processed, lang=lang))
        except Exception:
            texts.append(pytesseract.image_to_string(processed))
    return "\n".join(texts)


# Extensions d'images prises en charge par l'OCR.
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
# Extensions reconnues au total (images, PDF, texte déjà extrait).
SUPPORTED_SUFFIXES = IMAGE_SUFFIXES | {".pdf", ".txt"}


def extract_text(path: Union[str, Path], lang: str = "fra+eng") -> str:
    """Extrait le texte d'un fichier image, PDF ou texte selon son extension."""
    suffix = Path(path).suffix.lower()
    if suffix == ".txt":
        # Texte déjà reconnu : aucune dépendance OCR requise.
        return Path(path).read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        return pdf_to_text(path, lang=lang)
    if suffix in IMAGE_SUFFIXES:
        return image_to_text(path, lang=lang)
    raise ValueError(f"Format de fichier non pris en charge : {suffix}")


def scan_to_contact(path: Union[str, Path], lang: str = "fra+eng") -> Contact:
    """Pipeline complet : fichier -> OCR -> contact analysé."""
    text = extract_text(path, lang=lang)
    return parse_contact(text)
