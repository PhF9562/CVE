"""Reconnaissance optique de caractères (OCR) et prétraitement d'image.

Ce module isole les dépendances lourdes (OpenCV, Pillow, pytesseract, pdf2image)
et les importe paresseusement. Si elles ne sont pas installées, une
:class:`OCRUnavailableError` claire est levée plutôt qu'un ``ImportError`` opaque.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from . import config


class OCRUnavailableError(RuntimeError):
    """Levée lorsqu'une dépendance OCR requise est absente."""


def ocr_available() -> bool:
    """Indique si la chaîne OCR (pytesseract + Pillow) est utilisable."""
    try:  # pragma: no cover - dépend de l'environnement
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return True


def _require(module: str):
    try:
        return __import__(module)
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        raise OCRUnavailableError(
            f"Le module « {module} » est requis pour cette opération. "
            f"Installez les dépendances : pip install -r requirements.txt"
        ) from exc


def preprocess_image(pil_image):
    """Redresse, met en niveaux de gris et binarise une image PIL.

    Si OpenCV/numpy ne sont pas disponibles, on se rabat sur un simple
    passage en niveaux de gris via Pillow (l'OCR reste possible).
    """
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        return pil_image.convert("L")

    img = np.array(pil_image.convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Correction d'orientation (deskew) basée sur les pixels de texte.
    coords = np.column_stack(np.where(gray < 128))
    if coords.size:
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) > 0.5:
            h, w = gray.shape
            matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
            gray = cv2.warpAffine(
                gray, matrix, (w, h),
                flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
            )

    # Débruitage léger puis seuillage adaptatif (Otsu).
    gray = cv2.medianBlur(gray, 3)
    _, binarized = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    from PIL import Image
    return Image.fromarray(binarized)


def _load_images(path: Union[str, Path]) -> List:
    """Charge un fichier (image ou PDF) en une liste d'images PIL (une par page)."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in config.SUPPORTED_DOCUMENT_EXTENSIONS:
        try:
            from pdf2image import convert_from_path  # type: ignore
        except ImportError as exc:
            raise OCRUnavailableError(
                "Le module « pdf2image » (et l'outil poppler) est requis pour "
                "lire les PDF. Installez : pip install pdf2image"
            ) from exc
        return list(convert_from_path(str(path)))

    _require("PIL")
    from PIL import Image
    return [Image.open(path)]


def image_to_text(pil_image, languages: str | None = None) -> str:
    """Applique l'OCR sur une image PIL déjà prétraitée."""
    if not ocr_available():
        raise OCRUnavailableError(
            "pytesseract et Pillow sont requis pour l'OCR. "
            "Installez-les puis assurez-vous que le binaire Tesseract est présent."
        )
    import pytesseract

    return pytesseract.image_to_string(
        pil_image, lang=languages or config.OCR_LANGUAGES
    )


def extract_text(path: Union[str, Path], languages: str | None = None) -> str:
    """Pipeline complet : chargement -> prétraitement -> OCR -> texte concaténé."""
    pages = _load_images(path)
    texts: List[str] = []
    for page in pages:
        processed = preprocess_image(page)
        texts.append(image_to_text(processed, languages=languages))
    return "\n".join(texts).strip()
