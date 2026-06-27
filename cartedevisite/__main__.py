"""Permet de lancer l'application via ``python -m cartedevisite``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
