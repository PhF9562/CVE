"""Permet de lancer l'application avec ``python -m cartevisite``.

Options en ligne de commande :

* ``--db CHEMIN``      : base SQLite (défaut : ``contacts.db``) ;
* ``--export-dir DIR`` : dossier parent des exports (défaut : courant) ;
* ``--scan FICHIER``   : analyse un fichier en mode console (sans interface) ;
* ``--batch [DOSSIER]``: traite tout ``CV-Scan`` et exporte JSON + vCard.
"""

from __future__ import annotations

import argparse
import sys


def _scan_cli(path: str) -> int:
    from .ocr import scan_to_contact

    try:
        contact = scan_to_contact(path)
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    for key, value in contact.to_dict(include_id=False).items():
        if key == "raw_text":
            continue
        print(f"{key:>10} : {value}")
    return 0


def _batch_cli(base_dir, db_path, lang) -> int:
    from .batch import process_directory

    result = process_directory(base_dir=base_dir, lang=lang, db_path=db_path)
    print("\n" + result.summary())
    # Code de sortie non nul si rien n'a pu être extrait alors que des
    # scans étaient présents.
    if result.failures and not result.contacts:
        return 1
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cartevisite",
        description="Numérisation de cartes de visite.",
    )
    parser.add_argument("--db", default="contacts.db", help="Chemin de la base SQLite.")
    parser.add_argument("--export-dir", default=".", help="Dossier des exports.")
    parser.add_argument("--scan", metavar="FICHIER", help="Analyser un fichier en console puis quitter.")
    parser.add_argument(
        "--batch", nargs="?", const="", metavar="DOSSIER",
        help="Traiter tout le dossier CV-Scan (auto-détecté si non précisé) "
             "et exporter en JSON + vCard, puis quitter.",
    )
    parser.add_argument(
        "--lang", default="fra+eng",
        help="Langues Tesseract pour l'OCR (défaut : fra+eng).",
    )
    parser.add_argument(
        "--no-db", action="store_true",
        help="En mode --batch, ne pas enregistrer les contacts en base.",
    )
    args = parser.parse_args(argv)

    if args.scan:
        return _scan_cli(args.scan)

    if args.batch is not None:
        base_dir = args.batch or None  # "" => auto-détection
        db_path = None if args.no_db else args.db
        return _batch_cli(base_dir, db_path, args.lang)

    from .gui import App

    App(db_path=args.db, export_dir=args.export_dir).mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
