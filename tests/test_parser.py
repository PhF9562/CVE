"""Tests des heuristiques d'analyse du texte OCR."""

from cardscan.parser import (
    extract_email,
    extract_phone,
    extract_website,
    parse_text,
)


def test_extract_email():
    assert extract_email("Contactez jean.dupont@example.com svp") == "jean.dupont@example.com"
    assert extract_email("pas d'email ici") is None


def test_extract_email_lowercased():
    assert extract_email("Jean.DUPONT@Example.COM") == "jean.dupont@example.com"


def test_extract_website_ignores_email_domain():
    text = "marie@acme.com\nwww.acme-corp.com"
    assert extract_website(text) == "www.acme-corp.com"


def test_extract_phone_with_label():
    text = "Tél : +33 1 23 45 67 89\nMobile: 06 12 34 56 78"
    # La ligne étiquetée « Tél » est prioritaire.
    assert extract_phone(text) == "+33123456789"


def test_extract_phone_plain():
    assert extract_phone("Appelez le 01 23 45 67 89") == "0123456789"


def test_extract_phone_rejects_short_numbers():
    assert extract_phone("Code postal 75001") is None


def test_parse_full_card():
    text = (
        "Jean Dupont\n"
        "Directeur Commercial\n"
        "ACME SOLUTIONS SARL\n"
        "Tél : +33 1 23 45 67 89\n"
        "jean.dupont@acme.com\n"
        "www.acme.com"
    )
    contact = parse_text(text)
    assert contact.full_name == "Jean Dupont"
    assert "Directeur" in contact.job_title
    assert contact.email == "jean.dupont@acme.com"
    assert contact.phone == "+33123456789"
    assert contact.website == "www.acme.com"
    assert "ACME" in contact.company.upper()


def test_parse_guesses_name_from_email():
    contact = parse_text("marie.curie@radium.org")
    assert contact.email == "marie.curie@radium.org"
    assert contact.full_name == "Marie Curie"


def test_parse_empty():
    contact = parse_text("")
    assert contact.is_empty()


def test_company_from_uppercase_line():
    text = "Pierre Martin\nGLOBEX\npierre@globex.io"
    contact = parse_text(text)
    assert contact.company == "Globex"
