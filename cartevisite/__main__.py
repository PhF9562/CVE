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


def _batch_cli(base_dir, db_arg, no_db, lang, move_processed) -> int:
    from .batch import find_base_dir, process_directory

    base = find_base_dir(base_dir)
    if no_db:
        db_path = None
    elif db_arg is not None:
        db_path = db_arg  # chemin imposé par l'utilisateur
    else:
        # Par défaut, le carnet vit dans le dossier numérisation lui-même.
        db_path = base / "carnet.db"

    result = process_directory(
        base_dir=base, lang=lang, db_path=db_path, move_processed=move_processed
    )
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
    parser.add_argument(
        "--db", default=None,
        help="Chemin de la base SQLite (défaut : contacts.db pour l'interface, "
             "<numérisation>/carnet.db en mode --batch).",
    )
    parser.add_argument("--export-dir", default=None, help="Dossier des exports.")
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
    parser.add_argument(
        "--no-move", action="store_true",
        help="En mode --batch, ne pas déplacer les scans traités vers "
             "CV-Scan/traités.",
    )
    args = parser.parse_args(argv)

    if args.scan:
        return _scan_cli(args.scan)

    if args.batch is not None:
        base_dir = args.batch or None  # "" => auto-détection
        return _batch_cli(base_dir, args.db, args.no_db, args.lang, not args.no_move)

    from .gui import App

    App(db_path=args.db, export_dir=args.export_dir).mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
