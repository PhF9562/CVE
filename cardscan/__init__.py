"""CardScan – application personnelle de numérisation de cartes de visite.

Ce paquet regroupe les modules de l'application :

* :mod:`cardscan.parser`   – analyse du texte OCR pour en extraire les champs.
* :mod:`cardscan.database` – stockage local des contacts dans une base SQLite.
* :mod:`cardscan.export`   – export des contacts en JSON et vCard (.vcf).
* :mod:`cardscan.ocr`      – prétraitement d'image et reconnaissance optique.
* :mod:`cardscan.gui`      – interface graphique tkinter.

Les modules :mod:`cardscan.parser`, :mod:`cardscan.database` et
:mod:`cardscan.export` ne dépendent que de la bibliothèque standard et peuvent
donc être utilisés (et testés) sans installer OpenCV, Tesseract ou Tkinter.
"""

from .contact import Contact

__all__ = ["Contact"]
__version__ = "1.0.0"
