"""Export des contacts aux formats JSON et vCard (.vcf).

Conventions (cf. cahier des charges) :
  * JSON  -> dossier ``CV-JSON``
  * vCard -> dossier ``CV-VCF`` (un fichier .vcf par contact)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Union

from .models import Contact


def _slugify(value: str, fallback: str = "contact") -> str:
    """Transforme un libellé en nom de fichier sûr."""
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_-]+", "-", value).strip("-")
    return value or fallback


def _vcard_escape(value: str) -> str:
    """Échappe les caractères spéciaux d'une valeur vCard 3.0."""
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def contact_to_vcard(contact: Contact) -> str:
    """Sérialise un contact en vCard 3.0 (compatible Google/Outlook/Apple)."""
    lines = ["BEGIN:VCARD", "VERSION:3.0"]

    name = contact.name.strip()
    if name:
        parts = name.split()
        family = parts[-1] if len(parts) > 1 else ""
        given = " ".join(parts[:-1]) if len(parts) > 1 else parts[0]
        lines.append(f"N:{_vcard_escape(family)};{_vcard_escape(given)};;;")
        lines.append(f"FN:{_vcard_escape(name)}")
    else:
        # FN est obligatoire en vCard 3.0 : on utilise un libellé de repli.
        lines.append(f"FN:{_vcard_escape(contact.display_name())}")

    if contact.company.strip():
        lines.append(f"ORG:{_vcard_escape(contact.company.strip())}")
    if contact.title.strip():
        lines.append(f"TITLE:{_vcard_escape(contact.title.strip())}")
    if contact.phone.strip():
        lines.append(f"TEL;TYPE=WORK,VOICE:{_vcard_escape(contact.phone.strip())}")
    if contact.email.strip():
        lines.append(f"EMAIL;TYPE=WORK:{_vcard_escape(contact.email.strip())}")
    if contact.website.strip():
        lines.append(f"URL:{_vcard_escape(contact.website.strip())}")
    if contact.address.strip():
        addr = _vcard_escape(contact.address.strip())
        lines.append(f"ADR;TYPE=WORK:;;{addr};;;;")
    if contact.notes.strip():
        lines.append(f"NOTE:{_vcard_escape(contact.notes.strip())}")

    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


def export_json(
    contacts: Iterable[Contact],
    directory: Union[str, Path],
    filename: str = "contacts.json",
) -> Path:
    """Écrit tous les contacts dans un unique fichier JSON. Retourne le chemin."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    data = [c.to_dict(include_id=False) for c in contacts]
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def export_vcards(
    contacts: Iterable[Contact],
    directory: Union[str, Path],
) -> list[Path]:
    """Écrit un fichier .vcf par contact. Retourne la liste des chemins créés."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    used_names: set[str] = set()
    for index, contact in enumerate(contacts, start=1):
        base = _slugify(contact.display_name(), fallback=f"contact-{index}")
        name = base
        suffix = 2
        while name in used_names:
            name = f"{base}-{suffix}"
            suffix += 1
        used_names.add(name)

        path = directory / f"{name}.vcf"
        path.write_text(contact_to_vcard(contact), encoding="utf-8")
        paths.append(path)
    return paths
