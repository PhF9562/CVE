"""Reconnaissance optique de caractères (OCR) et prétraitement d'image.

Ce module dépend de bibliothèques optionnelles (OpenCV, Pillow, pytesseract,
pdf2image) ainsi que des moteurs système Tesseract et Poppler. Les imports sont
volontairement différés (« lazy ») afin que le reste de l'application reste
utilisable même si ces dépendances ne sont pas installées.

Utiliser :func:`verifier_dependances` pour savoir ce qui manque, puis
:func:`extraire_texte` pour obtenir le texte d'une image ou d'un PDF.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple


class OcrIndisponibleError(RuntimeError):
    """Levée lorsqu'une dépendance nécessaire à l'OCR est absente."""


def verifier_dependances() -> List[str]:
    """Retourne la liste des dépendances manquantes (vide si tout est présent)."""
    manquant: List[str] = []
    for module, paquet in (
        ("cv2", "opencv-python"),
        ("PIL", "Pillow"),
        ("pytesseract", "pytesseract"),
    ):
        try:
            __import__(module)
        except ImportError:
            manquant.append(paquet)

    # Tesseract lui-même.
    try:
        import pytesseract  # type: ignore

        pytesseract.get_tesseract_version()
    except Exception:
        if "pytesseract" not in manquant:
            manquant.append("tesseract-ocr (moteur système)")

    return manquant


def _charger_image_array(chemin: Path):
    """Charge une image (ou la 1re page d'un PDF) sous forme de tableau numpy BGR."""
    import numpy as np  # type: ignore

    if chemin.suffix.lower() == ".pdf":
        try:
            from pdf2image import convert_from_path  # type: ignore
        except ImportError as exc:  # pragma: no cover - dépend de l'environnement
            raise OcrIndisponibleError(
                "Le paquet 'pdf2image' (et Poppler) est requis pour lire les PDF."
            ) from exc
        pages = convert_from_path(str(chemin), dpi=300, first_page=1, last_page=1)
        if not pages:
            raise ValueError(f"Aucune page lisible dans le PDF : {chemin}")
        import cv2  # type: ignore

        return cv2.cvtColor(np.array(pages[0]), cv2.COLOR_RGB2BGR)

    import cv2  # type: ignore

    image = cv2.imread(str(chemin))
    if image is None:
        raise ValueError(f"Image illisible ou format non supporté : {chemin}")
    return image


def pretraiter(image):
    """Améliore une image pour l'OCR : niveaux de gris, débruitage, binarisation.

    ``image`` est un tableau numpy BGR (OpenCV). Retourne une image binaire.
    """
    import cv2  # type: ignore

    gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Débruitage léger préservant les contours.
    gris = cv2.bilateralFilter(gris, 9, 75, 75)
    # Binarisation adaptative robuste aux éclairages inégaux.
    binaire = cv2.adaptiveThreshold(
        gris,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15,
    )
    return binaire


def corriger_orientation(image):
    """Redresse l'image selon l'angle détecté par Tesseract (OSD).

    En cas d'échec de la détection, l'image originale est renvoyée inchangée.
    """
    import cv2  # type: ignore
    import pytesseract  # type: ignore

    try:
        osd = pytesseract.image_to_osd(image)
        angle = 0
        for ligne in osd.splitlines():
            if "Rotate:" in ligne:
                angle = int(ligne.split(":")[1].strip())
                break
        if angle % 360 == 0:
            return image
        # Rotation dans le sens horaire de l'angle indiqué.
        (h, w) = image.shape[:2]
        centre = (w // 2, h // 2)
        matrice = cv2.getRotationMatrix2D(centre, -angle, 1.0)
        return cv2.warpAffine(
            image, matrice, (w, h),
            flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception:
        return image


def extraire_texte(chemin: str | Path, langue: str = "fra+eng") -> str:
    """Extrait le texte d'une image ou d'un PDF de carte de visite.

    :param chemin: fichier image (JPG/PNG/…) ou PDF.
    :param langue: langues Tesseract (par défaut français + anglais).
    :raises OcrIndisponibleError: si une dépendance d'OCR est manquante.
    """
    manquant = verifier_dependances()
    if manquant:
        raise OcrIndisponibleError(
            "Dépendances OCR manquantes : " + ", ".join(manquant)
        )

    import pytesseract  # type: ignore

    chemin = Path(chemin)
    if not chemin.exists():
        raise FileNotFoundError(chemin)

    image = _charger_image_array(chemin)
    image = corriger_orientation(image)
    preparee = pretraiter(image)

    texte = pytesseract.image_to_string(preparee, lang=langue)
    return texte


def extraire_contact(chemin: str | Path, langue: str = "fra+eng"):
    """Raccourci : OCR puis analyse, renvoie un :class:`Contact`."""
    from .parser import analyser_texte

    texte = extraire_texte(chemin, langue=langue)
    return analyser_texte(texte)


# Extensions de fichiers acceptées par l'interface.
EXTENSIONS_SUPPORTEES: Tuple[str, ...] = (
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
    ".pdf",
)
