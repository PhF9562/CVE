#!/usr/bin/env python3
"""Point d'entrée de l'application de numérisation de cartes de visite.

Usage :

    python main.py                      # lance l'interface graphique
    python main.py scan carte.jpg       # OCR d'un fichier puis affichage (sans GUI)
    python main.py export-json          # exporte les contacts existants en JSON
    python main.py export-vcf           # exporte les contacts existants en vCard
    python main.py check                # vérifie les dépendances OCR

Répertoire de travail : par défaut, la base de contacts et les exports sont
rangés dans le dossier mémorisé (ou le dossier courant). On peut imposer un
autre dossier avec l'option ``--data-dir`` :

    python main.py --data-dir ~/MesCartes scan carte.jpg --enregistrer
    python main.py --data-dir ~/MesCartes export-vcf

Le mode graphique nécessite tkinter ; les modes en ligne de commande
fonctionnent sans interface.
"""

from __future__ import annotations

import argparse
import sys

from cartes_visite import config, exporter
from cartes_visite.database import CarnetAdresses


def _cmd_gui(args: argparse.Namespace) -> int:
    try:
        from cartes_visite.app import lancer_application
    except Exception as exc:  # noqa: BLE001
        print(f"Interface graphique indisponible : {exc}", file=sys.stderr)
        print("Essayez les commandes en ligne de commande (voir --help).", file=sys.stderr)
        return 1
    lancer_application(args.emplacement)
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    from cartes_visite import ocr

    manquant = ocr.verifier_dependances()
    if manquant:
        print("Dépendances OCR manquantes : " + ", ".join(manquant), file=sys.stderr)
        return 2

    contact = ocr.extraire_contact(args.fichier)
    print("Informations extraites :")
    for champ, valeur in contact.to_dict().items():
        if valeur:
            print(f"  {champ:12s}: {valeur}")

    if args.enregistrer:
        with CarnetAdresses(args.db) as carnet:
            carnet.ajouter(contact)
        print(f"\nContact enregistré dans : {args.db}")
    return 0


def _cmd_export_json(args: argparse.Namespace) -> int:
    with CarnetAdresses(args.db) as carnet:
        contacts = carnet.lister()
    if not contacts:
        print("Aucun contact à exporter.")
        return 0
    chemin = exporter.exporter_json(contacts, dossier=args.emplacement.dossier_json)
    print(f"{len(contacts)} contact(s) exporté(s) dans {chemin}")
    return 0


def _cmd_export_vcf(args: argparse.Namespace) -> int:
    with CarnetAdresses(args.db) as carnet:
        contacts = carnet.lister()
    if not contacts:
        print("Aucun contact à exporter.")
        return 0
    chemins = exporter.exporter_vcards(contacts, dossier=args.emplacement.dossier_vcf)
    print(f"{len(chemins)} fichier(s) .vcf créé(s) dans {args.emplacement.dossier_vcf}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    from cartes_visite import ocr

    manquant = ocr.verifier_dependances()
    if manquant:
        print("Dépendances OCR manquantes :")
        for m in manquant:
            print(f"  - {m}")
        return 1
    print("Toutes les dépendances OCR sont présentes.")
    return 0


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(
        description="Application de numérisation de cartes de visite."
    )
    parseur.add_argument(
        "--data-dir",
        dest="data_dir",
        default=None,
        help="Répertoire de travail (base de contacts + exports). "
        "Défaut : dernier dossier utilisé, sinon le dossier courant.",
    )
    parseur.add_argument(
        "--db",
        default=None,
        help="Chemin explicite de la base SQLite (remplace celui du répertoire de travail).",
    )
    sous = parseur.add_subparsers(dest="commande")

    sous.add_parser("gui", help="Lance l'interface graphique (défaut).")

    p_scan = sous.add_parser("scan", help="Analyse un fichier image/PDF.")
    p_scan.add_argument("fichier", help="Image ou PDF de la carte de visite.")
    p_scan.add_argument(
        "--enregistrer", action="store_true", help="Enregistre le contact détecté."
    )

    sous.add_parser("export-json", help="Exporte les contacts au format JSON.")
    sous.add_parser("export-vcf", help="Exporte les contacts au format vCard.")
    sous.add_parser("check", help="Vérifie la présence des dépendances OCR.")
    return parseur


def main(argv: list[str] | None = None) -> int:
    parseur = construire_parseur()
    args = parseur.parse_args(argv)

    # Résout le répertoire de travail puis les chemins concrets.
    args.emplacement = config.resoudre_emplacement(args.data_dir)
    # --db explicite a priorité sur le chemin du répertoire de travail.
    if args.db is None:
        args.db = str(args.emplacement.chemin_db)

    commandes = {
        None: _cmd_gui,
        "gui": _cmd_gui,
        "scan": _cmd_scan,
        "export-json": _cmd_export_json,
        "export-vcf": _cmd_export_vcf,
        "check": _cmd_check,
    }
    return commandes[args.commande](args)


if __name__ == "__main__":
    raise SystemExit(main())
