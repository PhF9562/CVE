"""Application personnelle de numérisation de cartes de visite.

Ce paquet regroupe la logique métier (base de données, analyse du texte OCR,
export JSON/vCard) et l'interface graphique tkinter. La logique métier ne
dépend pas des bibliothèques lourdes (OpenCV, Tesseract, Pillow) afin de
rester testable et utilisable sans elles.
"""

from .models import Contact

__all__ = ["Contact", "__version__"]

__version__ = "1.0.0"
