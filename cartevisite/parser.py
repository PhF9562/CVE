"""Analyse du texte OCR pour en extraire les champs d'un contact.

Le parseur applique une série d'heuristiques robustes :

* l'e-mail et le site web sont reconnus par expressions régulières ;
* le numéro de téléphone est détecté puis normalisé ;
* la fonction (poste) est repérée par un vocabulaire métier courant ;
* l'entreprise est devinée à partir des suffixes juridiques (SARL, Inc.…)
  ou d'une ligne en majuscules ;
* le nom complet est choisi parmi les lignes restantes les plus
  vraisemblables.

Aucune dépendance externe : la fonction :func:`parse_contact` opère sur
une simple chaîne de caractères et reste entièrement testable.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .models import Contact

# --- Expressions régulières -------------------------------------------------

EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
)

# URL avec ou sans schéma, en évitant de capturer une adresse e-mail.
WEBSITE_RE = re.compile(
    r"\b((?:https?://)?(?:www\.)?[A-Za-z0-9\-]+\.[A-Za-z]{2,}(?:/[^\s]*)?)\b",
)

# Séquence de téléphone : chiffres, espaces, points, tirets, parenthèses,
# précédée d'un éventuel indicatif international (+33, 00...).
PHONE_RE = re.compile(
    r"(?:(?:\+|00)\d{1,3}[\s.\-]?)?(?:\(?\d{1,4}\)?[\s.\-]?){2,6}\d",
)

# Étiquettes que l'on retire du début d'une ligne (« Tél : », « Email - »…).
LABEL_RE = re.compile(
    r"^\s*(?:t[ée]l(?:[ée]phone)?|mobile|gsm|portable|fax|mail|e[\-\s]?mail|"
    r"web|site|www|address?e?)\s*[:\-–]?\s*",
    re.IGNORECASE,
)

# Mots-clés indiquant une fonction / un poste.
TITLE_KEYWORDS = (
    "directeur", "directrice", "président", "presidente", "gérant", "gerante",
    "manager", "responsable", "chef", "ingénieur", "ingenieur", "consultant",
    "consultante", "développeur", "developpeur", "developer", "architecte",
    "comptable", "commercial", "commerciale", "assistant", "assistante",
    "fondateur", "fondatrice", "founder", "ceo", "cto", "cfo", "coo",
    "officer", "engineer", "head of", "lead", "designer", "avocat", "avocate",
    "notaire", "médecin", "medecin", "docteur", "dr.", "technicien",
    "technicienne", "chargé", "charge", "coordinateur", "coordinatrice",
    "analyste", "analyst",
)

# Suffixes juridiques / commerciaux révélant un nom d'entreprise.
COMPANY_SUFFIXES = (
    "sarl", "sas", "sasu", "eurl", "sa", "sci", "snc", "gie",
    "inc", "inc.", "llc", "ltd", "ltd.", "gmbh", "co", "co.",
    "corp", "corp.", "company", "group", "groupe", "studio",
    "agency", "agence", "solutions", "consulting", "technologies",
    "labs", "systems", "partners",
)


def _clean_line(line: str) -> str:
    """Retire une étiquette de tête et les espaces superflus."""
    return LABEL_RE.sub("", line).strip()


def normalize_phone(raw: str) -> str:
    """Normalise un numéro de téléphone détecté.

    On conserve un éventuel « + » initial et l'ensemble des chiffres, en
    supprimant les séparateurs décoratifs (espaces, points, tirets,
    parenthèses).
    """
    raw = raw.strip()
    has_plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    return ("+" + digits) if has_plus else digits


def _looks_like_phone(candidate: str) -> bool:
    """Un candidat est un téléphone plausible s'il contient assez de chiffres."""
    digits = re.sub(r"\D", "", candidate)
    return 6 <= len(digits) <= 15


def extract_email(text: str) -> str:
    match = EMAIL_RE.search(text)
    return match.group(0).strip().lower() if match else ""


def extract_phone(text: str) -> str:
    """Renvoie le premier numéro de téléphone plausible, normalisé."""
    for match in PHONE_RE.finditer(text):
        candidate = match.group(0)
        if _looks_like_phone(candidate):
            return normalize_phone(candidate)
    return ""


def extract_website(text: str, email: str = "") -> str:
    """Renvoie le premier site web, en ignorant le domaine de l'e-mail."""
    email_domain = email.split("@")[-1].lower() if "@" in email else ""
    # On retire d'abord toutes les adresses e-mail pour éviter de capturer
    # leur partie locale (« jean.dupont ») ou leur domaine comme site web.
    without_emails = EMAIL_RE.sub(" ", text)
    for match in WEBSITE_RE.finditer(without_emails):
        candidate = match.group(1).strip().rstrip(".,;")
        low = candidate.lower()
        # Ignore ce qui ressemble à un fragment d'adresse e-mail.
        if "@" in candidate:
            continue
        # Ignore le domaine déjà couvert par l'e-mail (sauf préfixe www).
        if email_domain and low.endswith(email_domain) and not low.startswith("www."):
            continue
        # Doit contenir un point et ne pas être un simple nombre décimal.
        if "." in candidate and not re.fullmatch(r"[\d.]+", candidate):
            return candidate
    return ""


def _find_title(lines: List[str]) -> Optional[str]:
    for line in lines:
        low = line.lower()
        if any(keyword in low for keyword in TITLE_KEYWORDS):
            return line.strip()
    return None


def _find_company(lines: List[str]) -> Optional[str]:
    # 1) Une ligne contenant un suffixe juridique l'emporte.
    for line in lines:
        tokens = re.split(r"[\s,.]+", line.lower())
        if any(token in COMPANY_SUFFIXES for token in tokens if token):
            return line.strip()
    # 2) À défaut, une ligne entièrement en majuscules (hors lignes courtes).
    for line in lines:
        letters = [c for c in line if c.isalpha()]
        if len(letters) >= 3 and line == line.upper():
            return line.strip()
    return None


def _looks_like_name(line: str) -> bool:
    """Heuristique : 2 à 4 mots, majoritairement alphabétiques."""
    words = line.split()
    if not (2 <= len(words) <= 4):
        return False
    alpha_words = [w for w in words if any(c.isalpha() for c in w)]
    if len(alpha_words) < 2:
        return False
    # Pas de chiffres (exclut adresses et téléphones).
    if any(c.isdigit() for c in line):
        return False
    return True


def _find_name(lines: List[str], excluded: set) -> Optional[str]:
    for line in lines:
        if line in excluded:
            continue
        if _looks_like_name(line):
            return line.strip()
    # Repli : première ligne non exclue et non vide.
    for line in lines:
        if line not in excluded and line.strip():
            return line.strip()
    return None


def parse_contact(text: str) -> Contact:
    """Analyse un bloc de texte OCR et renvoie un :class:`Contact`.

    L'algorithme procède du plus fiable (regex e-mail/téléphone) au plus
    incertain (nom de personne), en retirant au fur et à mesure les lignes
    déjà consommées pour ne pas réutiliser une information.
    """
    contact = Contact(raw_text=text)
    if not text or not text.strip():
        return contact

    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = [_clean_line(ln) for ln in raw_lines]
    cleaned = [ln for ln in cleaned if ln]

    # Champs structurés via regex (sur le texte complet).
    contact.email = extract_email(text)
    contact.phone = extract_phone(text)
    contact.website = extract_website(text, contact.email)

    # Lignes encore disponibles pour l'analyse sémantique : on écarte celles
    # qui ne portent qu'une information déjà extraite (email/phone/site seuls).
    excluded: set = set()
    for line in cleaned:
        only_email = extract_email(line) and _clean_line(EMAIL_RE.sub("", line)) == ""
        only_phone = _looks_like_phone(line) and not re.search(r"[A-Za-z]{3,}", line)
        if only_email or only_phone:
            excluded.add(line)

    available = [ln for ln in cleaned if ln not in excluded]

    title = _find_title(available)
    if title:
        contact.title = title
        excluded.add(title)
        available = [ln for ln in available if ln != title]

    company = _find_company(available)
    if company:
        contact.company = company
        excluded.add(company)
        available = [ln for ln in available if ln != company]

    name = _find_name(cleaned, excluded)
    if name:
        contact.full_name = name

    return contact
