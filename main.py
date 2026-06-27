#!/usr/bin/env python3
"""Lanceur de l'application de numérisation de cartes de visite.

Usage :
    python main.py            # lance l'interface graphique
    python main.py scan carte.jpg
    python main.py list
    python main.py export json
"""

from cartedevisite.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
