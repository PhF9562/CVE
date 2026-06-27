"""Application personnelle de numérisation de cartes de visite.

Ce paquet regroupe les modules nécessaires pour :

* extraire le texte d'une carte de visite via l'OCR (``ocr``) ;
* analyser ce texte pour reconnaître les champs de contact (``parser``) ;
* enregistrer les contacts dans une base SQLite locale (``database``) ;
* exporter les contacts au format JSON et vCard (``exporter``) ;
* offrir une interface graphique simple (``app``).

Les modules ``parser``, ``database`` et ``exporter`` ne dépendent que de la
bibliothèque standard de Python afin de rester testables et utilisables même
en l'absence des dépendances d'OCR/d'image.
"""

from .contact import Contact

__all__ = ["Contact"]
__version__ = "1.0.0"
