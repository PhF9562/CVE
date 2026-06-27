"""Tests de l'analyse du texte OCR."""

from cartedevisite.parser import parse_contact


def test_extracts_email():
    contact = parse_contact("Jean Dupont\nDirecteur\njean.dupont@example.com")
    assert contact.email == "jean.dupont@example.com"


def test_extracts_email_case_insensitive_and_trims_punctuation():
    contact = parse_contact("Contact: Marie.Curie@Example.COM.")
    assert contact.email == "marie.curie@example.com"


def test_extracts_phone_international():
    contact = parse_contact("Tel: +33 1 23 45 67 89")
    digits = "".join(c for c in contact.phone if c.isdigit())
    assert digits == "33123456789"


def test_extracts_phone_with_label_and_parens():
    contact = parse_contact("Téléphone : (01) 23 45 67 89")
    assert "23 45 67 89" in contact.phone


def test_ignores_short_number_as_phone():
    contact = parse_contact("Bureau 12\nSociété ACME SARL")
    assert contact.phone == ""


def test_extracts_website():
    contact = parse_contact("ACME\nwww.acme-corp.com\ncontact@acme.fr")
    assert contact.website == "www.acme-corp.com"


def test_website_not_confused_with_email_domain():
    contact = parse_contact("jean@acme.com")
    assert contact.email == "jean@acme.com"
    assert contact.website == ""


def test_detects_title_by_keyword():
    contact = parse_contact("Sophie Martin\nDirectrice Marketing\nACME")
    assert "Directrice" in contact.title


def test_detects_company_by_keyword():
    contact = parse_contact("Paul Durand\nConsultant\nDurand Solutions SAS")
    assert "Solutions" in contact.company


def test_detects_name():
    contact = parse_contact("Jean Dupont\nDirecteur Général\nMega Corp SARL\n+33 1 23 45 67 89")
    assert contact.name == "Jean Dupont"


def test_empty_text_returns_empty_contact():
    contact = parse_contact("")
    assert contact.is_empty()
    assert contact.raw_text == ""


def test_raw_text_preserved():
    text = "Jean Dupont\nDirecteur"
    contact = parse_contact(text)
    assert contact.raw_text == text


def test_full_card():
    text = (
        "MEGA CORP SARL\n"
        "Jean Dupont\n"
        "Directeur Commercial\n"
        "Tél : +33 1 44 55 66 77\n"
        "Email : jean.dupont@megacorp.fr\n"
        "www.megacorp.fr"
    )
    contact = parse_contact(text)
    assert contact.name == "Jean Dupont"
    assert "Directeur" in contact.title
    assert "MEGA CORP" in contact.company
    assert contact.email == "jean.dupont@megacorp.fr"
    assert contact.website == "www.megacorp.fr"
    assert "44 55 66 77" in contact.phone
