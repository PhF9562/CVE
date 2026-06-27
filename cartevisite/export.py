"""Export des contacts aux formats JSON et vCard (.vcf).

Conformément à la description de l'application :

* :func:`export_json` génère un fichier ``.json`` dans le dossier ``CV-JSON`` ;
* :func:`export_vcards` génère un fichier ``.vcf`` par contact dans ``CV-VCF``.

Le format vCard produit est conforme à la version 3.0, compatible avec
Google Contacts, Outlook et Apple Contacts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List, Union

from .models import Contact

JSON_DIR = "CV-JSON"
VCF_DIR = "CV-VCF"


# --- JSON -------------------------------------------------------------------

def contacts_to_json(contacts: Iterable[Contact]) -> str:
    """Sérialise une liste de contacts en chaîne JSON indentée."""
    payload = [c.to_dict(include_id=False) for c in contacts]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_json(
    contacts: Iterable[Contact],
    base_dir: Union[str, Path] = ".",
    filename: str = "contacts.json",
) -> Path:
    """Écrit tous les contacts dans ``<base_dir>/CV-JSON/<filename>``.

    Renvoie le chemin du fichier créé.
    """
    out_dir = Path(base_dir) / JSON_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(contacts_to_json(list(contacts)), encoding="utf-8")
    return out_path


# --- vCard ------------------------------------------------------------------

def _vcard_escape(value: str) -> str:
    """Échappe les caractères spéciaux d'un champ vCard (RFC 6350/2426)."""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _split_name(full_name: str) -> tuple[str, str]:
    """Sépare un nom complet en (prénom, nom de famille) au mieux.

    Convention vCard ``N`` : « Nom;Prénom ». On considère le dernier mot
    comme le nom de famille et le reste comme le prénom.
    """
    parts = full_name.split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[-1], " ".join(parts[:-1])


def contact_to_vcard(contact: Contact) -> str:
    """Renvoie la représentation vCard 3.0 d'un contact."""
    family, given = _split_name(contact.full_name)
    lines: List[str] = ["BEGIN:VCARD", "VERSION:3.0"]

    lines.append(f"N:{_vcard_escape(family)};{_vcard_escape(given)};;;")
    fn = contact.full_name.strip() or contact.display_label()
    lines.append(f"FN:{_vcard_escape(fn)}")

    if contact.company.strip():
        lines.append(f"ORG:{_vcard_escape(contact.company)}")
    if contact.title.strip():
        lines.append(f"TITLE:{_vcard_escape(contact.title)}")
    if contact.phone.strip():
        lines.append(f"TEL;TYPE=WORK,VOICE:{_vcard_escape(contact.phone)}")
    if contact.email.strip():
        lines.append(f"EMAIL;TYPE=WORK:{_vcard_escape(contact.email)}")
    if contact.website.strip():
        lines.append(f"URL:{_vcard_escape(contact.website)}")
    if contact.address.strip():
        # ADR : champs structurés ; on place l'adresse libre dans « rue ».
        lines.append(f"ADR;TYPE=WORK:;;{_vcard_escape(contact.address)};;;;")
    if contact.notes.strip():
        lines.append(f"NOTE:{_vcard_escape(contact.notes)}")

    lines.append("END:VCARD")
    # La vCard utilise CRLF comme séparateur de ligne.
    return "\r\n".join(lines) + "\r\n"


def _safe_filename(label: str, fallback: str) -> str:
    """Construit un nom de fichier sûr à partir d'un libellé de contact."""
    cleaned = re.sub(r"[^\w\-]+", "_", label, flags=re.UNICODE).strip("_")
    return cleaned or fallback


def export_vcards(
    contacts: Iterable[Contact],
    base_dir: Union[str, Path] = ".",
) -> List[Path]:
    """Écrit un fichier ``.vcf`` par contact dans ``<base_dir>/CV-VCF``.

    Renvoie la liste des chemins créés. Les noms de fichiers en collision
    sont suffixés pour rester uniques.
    """
    out_dir = Path(base_dir) / VCF_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: List[Path] = []
    used: set = set()
    for index, contact in enumerate(contacts, start=1):
        base = _safe_filename(contact.display_label(), f"contact_{index}")
        name = base
        suffix = 1
        while name.lower() in used:
            suffix += 1
            name = f"{base}_{suffix}"
        used.add(name.lower())

        out_path = out_dir / f"{name}.vcf"
        out_path.write_text(contact_to_vcard(contact), encoding="utf-8")
        paths.append(out_path)
    return paths
