"""Analyse du texte OCR pour en extraire les champs d'un contact.

Le moteur OCR renvoie un bloc de texte brut, ligne par ligne. Ce module
applique une série d'heuristiques (expressions régulières + mots-clés) pour
reconnaître l'e-mail, le téléphone, le site web, le nom, l'entreprise et la
fonction. L'objectif n'est pas la perfection mais une pré-extraction que
l'utilisateur pourra corriger dans l'écran récapitulatif.

Ce module ne dépend que de la bibliothèque standard.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .contact import Contact

# --------------------------------------------------------------------------
# Expressions régulières
# --------------------------------------------------------------------------
EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", re.UNICODE
)

# URL avec ou sans schéma ; on évite de capturer une adresse e-mail.
WEBSITE_RE = re.compile(
    r"\b(?:https?://)?(?:www\.)?[A-Za-z0-9\-]+\.(?:com|net|org|io|fr|co|eu|de|us|biz|info|app|dev)(?:/[^\s]*)?\b",
    re.IGNORECASE,
)

# Numéros de téléphone : on tolère +, espaces, points, tirets et parenthèses.
PHONE_RE = re.compile(
    r"(?:(?:\+|00)\d{1,3}[\s.\-]?)?(?:\(\d{1,4}\)[\s.\-]?)?\d(?:[\s.\-]?\d){6,11}"
)

# Mots-clés indiquant qu'une ligne précède/contient un numéro.
PHONE_KEYWORDS = re.compile(
    r"\b(t[ée]l|tel|phone|mobile|mob|gsm|fax|cell|portable|m|p|f)\b[.:]?",
    re.IGNORECASE,
)

# Mots-clés de fonction / poste.
JOB_KEYWORDS = re.compile(
    r"\b("
    r"directeur|directrice|président|présidente|gérant|gérante|"
    r"manager|director|ceo|cto|cfo|coo|founder|fondateur|fondatrice|"
    r"ingénieur|ingénieure|engineer|développeur|developer|consultant|consultante|"
    r"responsable|chef|head|lead|architect|architecte|designer|"
    r"commercial|commerciale|sales|marketing|comptable|avocat|avocate|"
    r"president|owner|partner|associé|associée|analyst|analyste|"
    r"technicien|technicienne|assistant|assistante|secrétaire|"
    r"officer|specialist|spécialiste|coordinateur|coordinatrice"
    r")\b",
    re.IGNORECASE,
)

# Suffixes qui trahissent une raison sociale.
COMPANY_KEYWORDS = re.compile(
    r"\b(inc|llc|ltd|gmbh|sarl|sas|sa|sasu|eurl|sprl|co|corp|company|"
    r"group|groupe|studio|agency|agence|solutions|technologies|consulting|"
    r"industries|partners|associates|s\.a\.|s\.a\.s\.|s\.a\.r\.l\.)\b",
    re.IGNORECASE,
)

# Un nom de personne plausible : 2 à 4 mots commençant par une majuscule.
NAME_RE = re.compile(
    r"^[A-ZÀ-Ÿ][\w'’\-]+(?:\s+[A-ZÀ-Ÿ][\w'’\-]+){1,3}$"
)


def _strip_phone_keyword(line: str) -> str:
    """Retire un éventuel libellé (Tél., Mobile…) en tête de ligne."""
    return PHONE_KEYWORDS.sub("", line).strip(" :.-\t")


def _normalize_phone(raw: str) -> str:
    """Nettoie un numéro tout en conservant un éventuel préfixe international."""
    raw = raw.strip()
    plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    return ("+" + digits) if plus else digits


def extract_email(text: str) -> Optional[str]:
    match = EMAIL_RE.search(text)
    return match.group(0).lower() if match else None


def extract_website(text: str) -> Optional[str]:
    # On masque d'abord les e-mails pour ne pas capturer leur domaine.
    masked = EMAIL_RE.sub(" ", text)
    for match in WEBSITE_RE.finditer(masked):
        candidate = match.group(0)
        return candidate.rstrip(".,;")
    return None


def extract_phone(text: str) -> Optional[str]:
    """Retourne le premier numéro de téléphone plausible du texte."""
    best: Optional[str] = None
    for line in text.splitlines():
        cleaned = _strip_phone_keyword(line)
        for match in PHONE_RE.finditer(cleaned):
            normalized = _normalize_phone(match.group(0))
            digit_count = len(re.sub(r"\D", "", normalized))
            # Un numéro a au moins 7 chiffres (sinon, faux positif).
            if 7 <= digit_count <= 15:
                # On privilégie les lignes étiquetées « tél/mobile ».
                if PHONE_KEYWORDS.search(line):
                    return normalized
                if best is None:
                    best = normalized
    return best


def _looks_like_name(line: str) -> bool:
    line = line.strip()
    if not NAME_RE.match(line):
        return False
    if EMAIL_RE.search(line) or WEBSITE_RE.search(line):
        return False
    if JOB_KEYWORDS.search(line) or COMPANY_KEYWORDS.search(line):
        return False
    if any(ch.isdigit() for ch in line):
        return False
    return True


def parse_text(text: str) -> Contact:
    """Analyse un bloc de texte OCR et renvoie un :class:`Contact`."""
    contact = Contact()
    if not text:
        return contact

    lines: List[str] = [ln.strip() for ln in text.splitlines() if ln.strip()]
    joined = "\n".join(lines)

    # Champs « durs » : e-mail, site, téléphone.
    if email := extract_email(joined):
        contact.email = email
    if website := extract_website(joined):
        contact.website = website
    if phone := extract_phone(joined):
        contact.phone = phone

    # Fonction : première ligne contenant un mot-clé de poste.
    for line in lines:
        if JOB_KEYWORDS.search(line) and not EMAIL_RE.search(line):
            contact.job_title = line
            break

    # Entreprise : ligne avec suffixe de société, ou ligne tout en majuscules.
    for line in lines:
        if line == contact.job_title:
            continue
        if COMPANY_KEYWORDS.search(line) and not EMAIL_RE.search(line):
            contact.company = line
            break
    if not contact.company:
        for line in lines:
            letters = [c for c in line if c.isalpha()]
            if (
                len(letters) >= 3
                and line.upper() == line
                and not EMAIL_RE.search(line)
                and not PHONE_RE.search(line)
                and line != contact.job_title
            ):
                contact.company = line.title()
                break

    # Nom : première ligne ressemblant à un nom de personne.
    for line in lines:
        if line in (contact.job_title, contact.company):
            continue
        if _looks_like_name(line):
            contact.full_name = line
            break

    # Repli : si l'e-mail existe mais pas le nom, on devine depuis l'adresse.
    if not contact.full_name and contact.email:
        local = contact.email.split("@", 1)[0]
        parts = re.split(r"[._\-]+", local)
        guess = " ".join(p.capitalize() for p in parts if p.isalpha())
        if guess and len(guess) > 2:
            contact.full_name = guess

    return contact
