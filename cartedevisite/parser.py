"""Analyse du texte OCR brut pour en extraire des champs de contact.

L'extraction repose sur des expressions régulières pour les champs structurés
(e-mail, téléphone, site web) et sur des heuristiques simples pour le nom, la
société et la fonction. L'objectif n'est pas la perfection mais de pré-remplir
l'écran de validation, l'utilisateur pouvant toujours corriger.
"""

from __future__ import annotations

import re
from typing import Optional

from .models import Contact

# --- Expressions régulières -------------------------------------------------

EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
)

# Site web : http(s):// ou www. ou domaine simple se terminant par un TLD
# connu. On évite de confondre avec une adresse e-mail (pas de @ juste avant).
URL_RE = re.compile(
    r"\b(?:https?://|www\.)[^\s,;]+"
    r"|\b[A-Za-z0-9\-]+\.(?:com|net|org|fr|io|co|eu|info|biz|dev|app)\b",
    re.IGNORECASE,
)

# Téléphone : séquences de chiffres avec séparateurs courants, indicatif
# international optionnel. Au moins 7 chiffres pour limiter les faux positifs.
PHONE_RE = re.compile(
    r"(?:(?:\+|00)\d{1,3}[\s.\-]?)?"
    r"(?:\(\d{1,4}\)[\s.\-]?)?"
    r"\d(?:[\s.\-]?\d){6,}",
)

# Mots typiques d'une fonction / d'un poste.
TITLE_KEYWORDS = (
    "directeur", "directrice", "manager", "responsable", "ingénieur",
    "ingenieur", "consultant", "président", "president", "ceo", "cto", "cfo",
    "coo", "fondateur", "founder", "developer", "développeur", "developpeur",
    "chef", "gérant", "gerant", "commercial", "architecte", "designer",
    "analyste", "technicien", "assistant", "associé", "associe", "head of",
    "lead", "officer", "vp", "vice-président", "vice-president", "avocat",
    "comptable", "notaire", "médecin", "medecin", "professeur", "coach",
)

# Indices d'une raison sociale.
COMPANY_KEYWORDS = (
    "sarl", "sas", "sasu", "eurl", "sa", "inc", "ltd", "llc", "gmbh", "ag",
    "group", "groupe", "company", "compagnie", "co.", "corp", "industries",
    "solutions", "technologies", "consulting", "studio", "agence", "agency",
    "bureau", "cabinet", "société", "societe", "&",
)

# Étiquettes à retirer en préfixe de ligne (ex. « Tel: », « Email : »).
LABEL_RE = re.compile(
    r"^\s*(?:t[ée]l(?:[ée]phone)?|mob(?:ile)?|gsm|fax|e[\-\s]?mail|mail|"
    r"web(?:site)?|site|adresse|address|portable|phone)\s*[:.\-]\s*",
    re.IGNORECASE,
)


def _clean_lines(text: str) -> list[str]:
    """Découpe le texte OCR en lignes nettoyées et non vides."""
    lines = []
    for raw in text.splitlines():
        line = raw.strip().strip("|•·*").strip()
        if line:
            lines.append(line)
    return lines


def _strip_label(line: str) -> str:
    return LABEL_RE.sub("", line).strip()


def _looks_like_name(line: str) -> bool:
    """Heuristique : 2 à 4 mots, majoritairement alphabétiques, sans chiffre."""
    if any(ch.isdigit() for ch in line) or "@" in line:
        return False
    words = line.split()
    if not (1 < len(words) <= 4):
        return False
    lowered = line.lower()
    if any(kw in lowered for kw in COMPANY_KEYWORDS):
        return False
    if any(kw in lowered for kw in TITLE_KEYWORDS):
        return False
    alpha = sum(c.isalpha() or c in " .'-" for c in line)
    return alpha / max(len(line), 1) > 0.8


def _extract_phone(text: str) -> str:
    best = ""
    for match in PHONE_RE.finditer(text):
        candidate = match.group().strip()
        digits = re.sub(r"\D", "", candidate)
        # Un téléphone plausible : entre 7 et 15 chiffres.
        if 7 <= len(digits) <= 15 and len(digits) >= len(re.sub(r"\D", "", best)):
            best = candidate
    return re.sub(r"\s{2,}", " ", best).strip()


def _extract_website(text: str, email: str) -> str:
    email_domain = email.split("@")[-1].lower() if "@" in email else ""
    for match in URL_RE.finditer(text):
        url = match.group().strip().rstrip(".,;")
        # Ignore si la « url » fait en réalité partie de l'e-mail détecté.
        if email and url.lower() in email.lower():
            continue
        if email_domain and url.lower() == email_domain:
            continue
        return url
    return ""


def parse_contact(text: str, raw_text: Optional[str] = None) -> Contact:
    """Analyse un texte OCR et retourne un :class:`Contact` pré-rempli.

    Args:
        text: texte issu de l'OCR.
        raw_text: texte brut à conserver (par défaut ``text``).
    """
    contact = Contact(raw_text=raw_text if raw_text is not None else text)
    if not text or not text.strip():
        return contact

    lines = _clean_lines(text)

    # E-mail (premier rencontré).
    email_match = EMAIL_RE.search(text)
    if email_match:
        contact.email = email_match.group().strip().rstrip(".,;").lower()

    # Téléphone et site web.
    contact.phone = _extract_phone(text)
    contact.website = _extract_website(text, contact.email)

    # Société et fonction par mots-clés.
    for line in lines:
        candidate = _strip_label(line)
        lowered = candidate.lower()
        if not contact.title and any(kw in lowered for kw in TITLE_KEYWORDS):
            contact.title = candidate
        elif not contact.company and any(kw in lowered for kw in COMPANY_KEYWORDS):
            contact.company = candidate

    # Nom : première ligne qui ressemble à un nom et n'est pas déjà utilisée.
    used = {contact.title, contact.company}
    for line in lines:
        candidate = _strip_label(line)
        if candidate in used:
            continue
        if _looks_like_name(candidate):
            contact.name = candidate
            break

    # Repli : si aucune société trouvée mais des lignes restent, on prend la
    # première ligne « texte » non attribuée comme société probable.
    if not contact.company:
        used = {contact.name, contact.title, contact.email}
        for line in lines:
            candidate = _strip_label(line)
            if candidate in used or "@" in candidate:
                continue
            if EMAIL_RE.search(candidate) or _extract_phone(candidate):
                continue
            if candidate and not _looks_like_name(candidate):
                contact.company = candidate
                break

    return contact
