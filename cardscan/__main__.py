"""Point d'entrée en ligne de commande : ``python -m cardscan``.

Sans argument, lance l'interface graphique. Avec un fichier ou un dossier en
argument, effectue l'OCR en mode console (utile pour tester sans affichage)::

    python -m cardscan                      # interface graphique
    python -m cardscan carte.jpg            # OCR d'un fichier
    python -m cardscan carte.jpg --json     # sortie JSON
    python -m cardscan ./cartes/            # balaye un dossier (récursif)
    python -m cardscan ./cartes/ --save     # ...et enregistre dans le carnet
    python -m cardscan ./cartes/ --no-recursive
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _print_contact(contact, as_json: bool) -> None:
    data = contact.to_dict(include_id=False)
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for attr, value in data.items():
            if value:
                print(f"{attr:12}: {value}")


def _scan_file(path: str, args) -> int:
    from .ocr import OCRUnavailableError, scan_card

    try:
        contact = scan_card(path)
    except (OCRUnavailableError, FileNotFoundError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    _print_contact(contact, args.json)
    if args.save and not contact.is_empty():
        from .database import ContactDatabase

        with ContactDatabase() as db:
            db.add(contact)
        print(f"\n→ Contact enregistré dans le carnet.", file=sys.stderr)
    return 0


def _scan_dir(path: str, args) -> int:
    from .ocr import OCRUnavailableError
    from .scanner import find_card_files, scan_directory

    recursive = not args.no_recursive
    try:
        files = find_card_files(path, recursive=recursive)
    except NotADirectoryError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    if not files:
        print("Aucun fichier analysable (image ou PDF) trouvé dans le dossier.")
        return 0

    print(f"{len(files)} fichier(s) à analyser dans {path}\n", file=sys.stderr)

    def _progress(index, total, file_path):
        print(f"[{index}/{total}] {file_path.name}", file=sys.stderr)

    try:
        results = scan_directory(path, recursive=recursive, progress=_progress)
    except OCRUnavailableError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    ok = [r for r in results if r.ok and not r.contact.is_empty()]
    failed = [r for r in results if not r.ok]
    contacts = [r.contact for r in ok]

    if args.json:
        payload = [
            {"file": str(r.path), "contact": r.contact.to_dict(include_id=False)}
            for r in ok
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for r in ok:
            print(f"\n=== {r.path.name} ===")
            _print_contact(r.contact, False)

    # Balayage de dossier : on enregistre chaque carte dans le carnet, puis on
    # exporte automatiquement les deux formats dans leurs répertoires dédiés.
    if contacts:
        from .database import ContactDatabase

        with ContactDatabase() as db:
            for contact in contacts:
                db.add(contact)
        print(
            f"\n→ {len(contacts)} contact(s) enregistré(s) dans le carnet.",
            file=sys.stderr,
        )

        from . import export

        export_dir = Path(args.export_dir) if args.export_dir else Path(path)
        json_path = export.export_json(contacts, export_dir)
        vcf_paths = export.export_vcards(contacts, export_dir)
        print(f"→ Export JSON  : {json_path}", file=sys.stderr)
        print(
            f"→ Export vCard : {len(vcf_paths)} fichier(s) dans "
            f"{export_dir / export.VCF_DIR_NAME}",
            file=sys.stderr,
        )

    print(
        f"\nBilan : {len(ok)} carte(s) analysée(s), {len(failed)} échec(s).",
        file=sys.stderr,
    )
    for r in failed:
        print(f"  ✗ {r.path.name} : {r.error}", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cardscan",
        description="Numérisation de cartes de visite (OCR + export).",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Fichier (image/PDF) ou dossier à analyser. "
        "Sans argument : interface graphique.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Affiche le résultat en JSON au lieu d'un format lisible.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Pour un fichier unique : enregistre le contact dans le carnet. "
        "(Le balayage d'un dossier enregistre et exporte toujours.)",
    )
    parser.add_argument(
        "--export-dir",
        metavar="DOSSIER",
        help="Dossier où créer CV-JSON/ et CV-VCF/ lors d'un balayage. "
        "Par défaut : le dossier balayé.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Pour un dossier : ne pas explorer les sous-dossiers.",
    )
    args = parser.parse_args(argv)

    if args.path is None:
        from .gui import run

        run()
        return 0

    if Path(args.path).is_dir():
        return _scan_dir(args.path, args)
    return _scan_file(args.path, args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
