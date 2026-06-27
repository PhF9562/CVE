"""Interface en ligne de commande.

Sans argument (ou avec ``gui``), lance l'interface graphique. Les sous-commandes
permettent un usage sans écran : numériser un fichier, lister, exporter — utile
pour les tests et l'automatisation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config, export
from .database import ContactDatabase
from .parser import parse_contact


def _open_db() -> ContactDatabase:
    config.ensure_dirs()
    return ContactDatabase(config.DATABASE_PATH)


def cmd_gui(_args) -> int:
    try:
        from . import gui
    except Exception as exc:  # noqa: BLE001 - tkinter peut manquer
        print(f"Interface graphique indisponible : {exc}", file=sys.stderr)
        return 1
    gui.run()
    return 0


def cmd_scan(args) -> int:
    from . import ocr

    try:
        text = ocr.extract_text(args.path)
    except ocr.OCRUnavailableError as exc:
        print(f"OCR indisponible : {exc}", file=sys.stderr)
        return 2

    contact = parse_contact(text)
    if contact.is_empty():
        print("Aucune information exploitable détectée.", file=sys.stderr)
        if not args.force:
            return 3

    with _open_db() as db:
        contact_id = db.add(contact)
    print(f"Contact #{contact_id} enregistré : {contact.display_name()}")
    for key in ("name", "company", "title", "phone", "email", "website"):
        value = getattr(contact, key)
        if value:
            print(f"  {key}: {value}")
    return 0


def cmd_list(_args) -> int:
    with _open_db() as db:
        contacts = db.all()
    if not contacts:
        print("Aucun contact enregistré.")
        return 0
    for contact in contacts:
        print(f"#{contact.id:>3}  {contact.display_name():<30}  {contact.email}  {contact.phone}")
    return 0


def cmd_export(args) -> int:
    with _open_db() as db:
        contacts = db.all()
    if not contacts:
        print("Aucun contact à exporter.", file=sys.stderr)
        return 1

    if args.format in ("json", "all"):
        path = export.export_json(contacts, config.JSON_EXPORT_DIR)
        print(f"JSON  -> {path}")
    if args.format in ("vcard", "vcf", "all"):
        paths = export.export_vcards(contacts, config.VCF_EXPORT_DIR)
        print(f"vCard -> {len(paths)} fichier(s) dans {config.VCF_EXPORT_DIR}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cartedevisite",
        description="Numérisation et gestion de cartes de visite.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("gui", help="Lancer l'interface graphique (par défaut).")

    p_scan = sub.add_parser("scan", help="Numériser un fichier image/PDF.")
    p_scan.add_argument("path", type=Path, help="Chemin de l'image ou du PDF.")
    p_scan.add_argument("--force", action="store_true",
                        help="Enregistrer même si rien n'est détecté.")

    sub.add_parser("list", help="Lister les contacts enregistrés.")

    p_export = sub.add_parser("export", help="Exporter les contacts.")
    p_export.add_argument("format", choices=("json", "vcard", "vcf", "all"),
                          nargs="?", default="all")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "gui": cmd_gui,
        "scan": cmd_scan,
        "list": cmd_list,
        "export": cmd_export,
        None: cmd_gui,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
