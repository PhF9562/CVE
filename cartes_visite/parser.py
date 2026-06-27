"""Analyse du texte OCR pour reconnaître les champs d'un contact.

Ce module ne dépend que de la bibliothèque standard. Il applique une série
d'heuristiques (expressions régulières et mots-clés) sur le texte brut renvoyé
par l'OCR pour en déduire le nom, l'entreprise, le poste, le téléphone,
l'e-mail, le site web et l'adresse.
"""

from __future__ import annotations

import re
from typing import List

from .contact import Contact

# --- Expressions régulières ------------------------------------------------

_EMAIL_RE = re.compile(
    r"[\w.%+\-]+@[\w.\-]+\.\w{2,}",
    re.UNICODE,
)

# Numéro de téléphone : tolérant aux espaces, points, tirets, parenthèses
# et préfixe international. On exige au moins 8 chiffres au total.
_TEL_RE = re.compile(
    r"(?:(?:\+|00)\d{1,3}[\s.\-]?)?(?:\(\d+\)[\s.\-]?)?(?:\d[\s.\-]?){7,}\d",
)

_URL_RE = re.compile(
    r"\b((?:https?://)?(?:www\.)?[A-Za-z0-9\-]+\.[A-Za-z]{2,}(?:/[^\s]*)?)\b",
)

# Postes / fonctions courants (français et anglais) pour repérer la ligne « poste ».
_MOTS_POSTE = (
    "directeur",
    "directrice",
    "président",
    "presidente",
    "gérant",
    "gerant",
    "manager",
    "responsable",
    "chef",
    "ingénieur",
    "ingenieur",
    "développeur",
    "developpeur",
    "developer",
    "consultant",
    "commercial",
    "comptable",
    "assistant",
    "assistante",
    "chargé",
    "charge",
    "fondateur",
    "fondatrice",
    "founder",
    "ceo",
    "cto",
    "cfo",
    "coo",
    "vp",
    "head of",
    "lead",
    "architecte",
    "designer",
    "avocat",
    "médecin",
    "medecin",
    "technicien",
    "secrétaire",
    "secretaire",
    "vendeur",
    "vendeuse",
)

# Indices indiquant qu'une ligne est une entreprise plutôt qu'un nom de personne.
_MOTS_ENTREPRISE = (
    "sarl",
    "sas",
    "sasu",
    "sa",
    "eurl",
    "inc",
    "ltd",
    "llc",
    "gmbh",
    "corp",
    "company",
    "compagnie",
    "société",
    "societe",
    "group",
    "groupe",
    "studio",
    "agence",
    "agency",
    "consulting",
    "solutions",
    "technologies",
    "systems",
    "industries",
    "entreprise",
)

# Indices d'une ligne d'adresse postale.
_MOTS_ADRESSE = (
    "rue",
    "avenue",
    "av.",
    "boulevard",
    "bvd",
    "bd",
    "impasse",
    "chemin",
    "place",
    "allée",
    "allee",
    "route",
    "quai",
    "cours",
    "zone",
    "zi",
    "za",
    "bp",
    "cedex",
    "street",
    "st.",
    "road",
    "rd",
    "po box",
    "suite",
)

_CODE_POSTAL_RE = re.compile(r"\b\d{4,5}\b")


def _nettoyer_lignes(texte: str) -> List[str]:
    """Découpe le texte en lignes nettoyées et non vides."""
    lignes = []
    for brute in texte.splitlines():
        ligne = brute.strip().strip("|").strip()
        # Supprime les caractères de bruit isolés laissés par l'OCR.
        ligne = re.sub(r"\s{2,}", " ", ligne)
        if ligne:
            lignes.append(ligne)
    return lignes


def _normaliser_telephone(brut: str) -> str:
    """Normalise un numéro de téléphone en ne gardant que '+' et les chiffres groupés."""
    nettoye = re.sub(r"[^\d+]", "", brut)
    return nettoye


def _ligne_contient_mot(ligne: str, mots) -> bool:
    bas = ligne.lower()
    return any(re.search(r"\b" + re.escape(mot) + r"\b", bas) for mot in mots)


def _ressemble_a_un_nom(ligne: str) -> bool:
    """Heuristique : 2 à 4 mots, principalement alphabétiques, sans chiffre."""
    if any(c.isdigit() for c in ligne):
        return False
    mots = ligne.split()
    if not (1 < len(mots) <= 4):
        return False
    alpha = sum(c.isalpha() or c in " -'." for c in ligne)
    return alpha / max(len(ligne), 1) > 0.8


def analyser_texte(texte: str) -> Contact:
    """Analyse le texte OCR brut et retourne un :class:`Contact`.

    L'algorithme procède en deux temps :

    1. extraction des champs « forts » repérables par motif (e-mail, téléphone,
       site web) ;
    2. classement des lignes restantes (poste, entreprise, adresse, nom) à
       l'aide de mots-clés et d'heuristiques de forme.
    """
    contact = Contact()
    lignes = _nettoyer_lignes(texte)

    lignes_restantes: List[str] = []

    for ligne in lignes:
        consommee = False

        # E-mail (prend le premier rencontré).
        if not contact.email:
            m = _EMAIL_RE.search(ligne)
            if m:
                contact.email = m.group(0).lower()
                # La ligne peut ne contenir que l'e-mail.
                reste = (ligne[: m.start()] + ligne[m.end():]).strip(" :|-")
                if not reste:
                    consommee = True

        # Site web (mais pas une adresse e-mail détectée comme domaine).
        if not contact.site_web and "@" not in ligne:
            m = _URL_RE.search(ligne)
            if m and not _EMAIL_RE.search(ligne):
                url = m.group(1)
                # Évite de confondre un simple domaine d'e-mail.
                if "." in url:
                    contact.site_web = url
                    reste = (ligne[: m.start()] + ligne[m.end():]).strip(" :|-")
                    if not reste:
                        consommee = True

        # Téléphone : on accepte plusieurs numéros mais on garde le premier.
        if not contact.telephone:
            m = _TEL_RE.search(ligne)
            if m:
                normalise = _normaliser_telephone(m.group(0))
                if len(re.sub(r"\D", "", normalise)) >= 8:
                    contact.telephone = normalise
                    consommee = True

        if not consommee:
            lignes_restantes.append(ligne)

    # --- Classement des lignes restantes -----------------------------------
    candidats_nom: List[str] = []

    for ligne in lignes_restantes:
        if not contact.poste and _ligne_contient_mot(ligne, _MOTS_POSTE):
            contact.poste = ligne
            continue
        if not contact.entreprise and _ligne_contient_mot(ligne, _MOTS_ENTREPRISE):
            contact.entreprise = ligne
            continue
        if _ligne_contient_mot(ligne, _MOTS_ADRESSE) or _CODE_POSTAL_RE.search(ligne):
            contact.adresse = (contact.adresse + " " + ligne).strip() if contact.adresse else ligne
            continue
        candidats_nom.append(ligne)

    # Le nom est le meilleur candidat ressemblant à un nom de personne,
    # sinon la première ligne restante (souvent en haut de la carte).
    if candidats_nom:
        noms_probables = [l for l in candidats_nom if _ressemble_a_un_nom(l)]
        if noms_probables:
            contact.nom = noms_probables[0]
            candidats_nom.remove(noms_probables[0])
        else:
            contact.nom = candidats_nom.pop(0)

        # Une entreprise non encore trouvée peut être un des candidats restants.
        if not contact.entreprise and candidats_nom:
            contact.entreprise = candidats_nom[0]

    return contact
