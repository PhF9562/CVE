"""Application personnelle de numérisation de cartes de visite.

Ce paquet regroupe les modules métier de l'application :

* :mod:`cartevisite.models`   – structure de données d'un contact ;
* :mod:`cartevisite.parser`   – extraction des champs depuis le texte OCR ;
* :mod:`cartevisite.ocr`      – prétraitement d'image et reconnaissance de texte ;
* :mod:`cartevisite.database` – stockage local SQLite ;
* :mod:`cartevisite.export`   – export JSON et vCard (.vcf) ;
* :mod:`cartevisite.gui`      – interface graphique tkinter.

Le cœur métier (modèles, parseur, base, export) ne dépend d'aucune
bibliothèque externe : il peut donc être testé sans Tesseract, sans
OpenCV et sans serveur d'affichage.
"""

from .models import Contact

__all__ = ["Contact", "__version__"]

__version__ = "1.0.0"
