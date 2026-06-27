"""Point d'entrée en ligne de commande : ``python -m cardscan``.

Sans argument, lance l'interface graphique. Avec un fichier en argument,
effectue l'OCR en mode console (utile pour tester sans affichage)::

    python -m cardscan                 # interface graphique
    python -m cardscan carte.jpg       # OCR + affichage des champs
    python -m cardscan carte.jpg --json
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cardscan",
        description="Numérisation de cartes de visite (OCR + export).",
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Image ou PDF à analyser. Sans fichier : interface graphique.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Affiche le résultat en JSON au lieu d'un format lisible.",
    )
    args = parser.parse_args(argv)

    if args.file is None:
        from .gui import run

        run()
        return 0

    from .ocr import OCRUnavailableError, scan_card

    try:
        contact = scan_card(args.file)
    except (OCRUnavailableError, FileNotFoundError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(contact.to_dict(include_id=False), ensure_ascii=False, indent=2))
    else:
        for attr, value in contact.to_dict(include_id=False).items():
            if value:
                print(f"{attr:12}: {value}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
