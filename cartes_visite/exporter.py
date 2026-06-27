"""Export des contacts vers les formats JSON et vCard (.vcf).

Seule la bibliothèque standard est utilisée. Les fichiers sont écrits dans des
dossiers dédiés (``CV-JSON`` et ``CV-VCF`` par défaut).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List

from .contact import Contact

DOSSIER_JSON = "CV-JSON"
DOSSIER_VCF = "CV-VCF"

_CHAMPS_EXPORT = (
    "nom",
    "entreprise",
    "poste",
    "telephone",
    "email",
    "site_web",
    "adresse",
    "notes",
)


def _nom_fichier_sur(contact: Contact, defaut: str = "contact") -> str:
    """Construit un nom de fichier sûr à partir du nom/entreprise du contact."""
    base = contact.nom or contact.entreprise or contact.email or defaut
    base = base.strip().lower()
    base = re.sub(r"[^\w\-]+", "_", base, flags=re.UNICODE).strip("_")
    base = base or defaut
    if contact.id is not None:
        base = f"{base}_{contact.id}"
    return base


def _echapper_vcard(valeur: str) -> str:
    """Échappe les caractères spéciaux selon la RFC 6350 (vCard 3.0)."""
    return (
        valeur.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def contact_vers_vcard(contact: Contact) -> str:
    """Retourne la représentation vCard 3.0 d'un contact."""
    lignes = ["BEGIN:VCARD", "VERSION:3.0"]

    nom = contact.nom or contact.entreprise or "Contact"
    lignes.append(f"FN:{_echapper_vcard(nom)}")

    # N : nom de famille; prénom; ... (découpage simple sur le dernier espace).
    morceaux = contact.nom.split()
    if len(morceaux) >= 2:
        famille = _echapper_vcard(morceaux[-1])
        prenom = _echapper_vcard(" ".join(morceaux[:-1]))
        lignes.append(f"N:{famille};{prenom};;;")
    else:
        lignes.append(f"N:{_echapper_vcard(contact.nom)};;;;")

    if contact.entreprise:
        lignes.append(f"ORG:{_echapper_vcard(contact.entreprise)}")
    if contact.poste:
        lignes.append(f"TITLE:{_echapper_vcard(contact.poste)}")
    if contact.telephone:
        lignes.append(f"TEL;TYPE=WORK,VOICE:{_echapper_vcard(contact.telephone)}")
    if contact.email:
        lignes.append(f"EMAIL;TYPE=WORK:{_echapper_vcard(contact.email)}")
    if contact.site_web:
        lignes.append(f"URL:{_echapper_vcard(contact.site_web)}")
    if contact.adresse:
        # ADR : boîte postale; étendue; rue; ville; région; code; pays.
        lignes.append(f"ADR;TYPE=WORK:;;{_echapper_vcard(contact.adresse)};;;;")
    if contact.notes:
        lignes.append(f"NOTE:{_echapper_vcard(contact.notes)}")

    lignes.append("END:VCARD")
    # La vCard utilise des fins de ligne CRLF.
    return "\r\n".join(lignes) + "\r\n"


def exporter_json(
    contacts: Iterable[Contact],
    dossier: str | Path = DOSSIER_JSON,
    nom_fichier: str = "contacts.json",
) -> Path:
    """Exporte tous les contacts dans un unique fichier JSON.

    Retourne le chemin du fichier créé.
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / nom_fichier

    donnees = []
    for contact in contacts:
        d = {champ: getattr(contact, champ) for champ in _CHAMPS_EXPORT}
        if contact.id is not None:
            d["id"] = contact.id
        donnees.append(d)

    cible.write_text(
        json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return cible


def exporter_vcards(
    contacts: Iterable[Contact],
    dossier: str | Path = DOSSIER_VCF,
) -> List[Path]:
    """Exporte chaque contact dans son propre fichier .vcf.

    Retourne la liste des chemins créés.
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)

    chemins: List[Path] = []
    noms_utilises: set[str] = set()

    for contact in contacts:
        base = _nom_fichier_sur(contact)
        # Évite les collisions de noms de fichiers.
        nom = base
        suffixe = 1
        while nom in noms_utilises:
            suffixe += 1
            nom = f"{base}_{suffixe}"
        noms_utilises.add(nom)

        cible = dossier / f"{nom}.vcf"
        cible.write_text(contact_vers_vcard(contact), encoding="utf-8")
        chemins.append(cible)

    return chemins
