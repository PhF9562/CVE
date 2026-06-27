"""Export des contacts en JSON et vCard (.vcf).

* L'export JSON produit un unique fichier ``contacts.json`` dans le dossier
  ``CV-JSON`` contenant la liste de tous les champs.
* L'export vCard produit un fichier ``.vcf`` par contact dans le dossier
  ``CV-VCF`` (format 3.0, compatible Google/Apple/Outlook Contacts).

Ce module ne dépend que de la bibliothèque standard.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List, Union

from .contact import Contact

JSON_DIR_NAME = "CV-JSON"
VCF_DIR_NAME = "CV-VCF"


# --------------------------------------------------------------------------
# JSON
# --------------------------------------------------------------------------
def export_json(
    contacts: Iterable[Contact],
    out_dir: Union[str, Path],
    filename: str = "contacts.json",
) -> Path:
    """Écrit tous les contacts dans un fichier JSON et renvoie son chemin."""
    directory = Path(out_dir) / JSON_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    data = [c.to_dict(include_id=False) for c in contacts]
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target


# --------------------------------------------------------------------------
# vCard
# --------------------------------------------------------------------------
def _vcard_escape(value: str) -> str:
    """Échappe les caractères spéciaux selon la RFC 6350."""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _split_name(full_name: str) -> tuple:
    """Sépare un nom complet en (nom de famille, prénom) pour le champ N."""
    parts = full_name.split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    # Convention vCard : Famille;Prénom — on suppose « Prénom … Nom ».
    return parts[-1], " ".join(parts[:-1])


def contact_to_vcard(contact: Contact) -> str:
    """Sérialise un contact au format vCard 3.0."""
    family, given = _split_name(contact.full_name)
    lines: List[str] = ["BEGIN:VCARD", "VERSION:3.0"]

    lines.append(f"N:{_vcard_escape(family)};{_vcard_escape(given)};;;")
    display = contact.full_name or contact.display_name()
    lines.append(f"FN:{_vcard_escape(display)}")

    if contact.company:
        lines.append(f"ORG:{_vcard_escape(contact.company)}")
    if contact.job_title:
        lines.append(f"TITLE:{_vcard_escape(contact.job_title)}")
    if contact.email:
        lines.append(f"EMAIL;TYPE=INTERNET,WORK:{_vcard_escape(contact.email)}")
    if contact.phone:
        lines.append(f"TEL;TYPE=WORK,VOICE:{_vcard_escape(contact.phone)}")
    if contact.website:
        lines.append(f"URL:{_vcard_escape(contact.website)}")
    if contact.address:
        lines.append(f"ADR;TYPE=WORK:;;{_vcard_escape(contact.address)};;;;")
    if contact.notes:
        lines.append(f"NOTE:{_vcard_escape(contact.notes)}")

    lines.append("END:VCARD")
    # La RFC impose une terminaison CRLF.
    return "\r\n".join(lines) + "\r\n"


def _safe_filename(name: str, fallback: str) -> str:
    """Produit un nom de fichier sûr à partir d'un libellé de contact."""
    cleaned = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE).strip("_")
    return cleaned or fallback


def export_vcards(
    contacts: Iterable[Contact],
    out_dir: Union[str, Path],
) -> List[Path]:
    """Écrit un fichier ``.vcf`` par contact, renvoie la liste des chemins."""
    directory = Path(out_dir) / VCF_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    used_names: dict = {}
    for index, contact in enumerate(contacts, start=1):
        base = _safe_filename(contact.display_name(), f"contact_{index}")
        # On évite les collisions de noms de fichiers.
        count = used_names.get(base, 0)
        used_names[base] = count + 1
        if count:
            base = f"{base}_{count + 1}"
        target = directory / f"{base}.vcf"
        target.write_text(contact_to_vcard(contact), encoding="utf-8")
        written.append(target)
    return written


def export_single_vcard(
    contact: Contact, out_dir: Union[str, Path]
) -> Path:
    """Export d'un seul contact (utilisé par le bouton « Exporter »)."""
    return export_vcards([contact], out_dir)[0]
