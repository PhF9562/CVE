"""Tests de l'export JSON et vCard."""

import json

from cardscan.contact import Contact
from cardscan import export


def sample_contacts():
    return [
        Contact(
            full_name="Jean Dupont",
            company="ACME SARL",
            job_title="Directeur",
            email="jean@acme.com",
            phone="+33123456789",
            website="www.acme.com",
        ),
        Contact(full_name="Marie Curie", email="marie@radium.org"),
    ]


def test_export_json_roundtrip(tmp_path):
    contacts = sample_contacts()
    path = export.export_json(contacts, tmp_path)
    assert path.exists()
    assert path.parent.name == export.JSON_DIR_NAME

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["full_name"] == "Jean Dupont"
    # L'identifiant interne ne doit pas fuiter dans l'export.
    assert "id" not in data[0]
    restored = Contact.from_dict(data[0])
    assert restored.email == "jean@acme.com"


def test_export_vcards_one_file_each(tmp_path):
    contacts = sample_contacts()
    paths = export.export_vcards(contacts, tmp_path)
    assert len(paths) == 2
    for p in paths:
        assert p.suffix == ".vcf"
        assert p.parent.name == export.VCF_DIR_NAME


def test_vcard_content():
    contact = Contact(
        full_name="Jean Dupont",
        company="ACME SARL",
        job_title="Directeur",
        email="jean@acme.com",
        phone="+33123456789",
        website="www.acme.com",
    )
    vcf = export.contact_to_vcard(contact)
    assert vcf.startswith("BEGIN:VCARD")
    assert vcf.strip().endswith("END:VCARD")
    assert "VERSION:3.0" in vcf
    assert "FN:Jean Dupont" in vcf
    assert "N:Dupont;Jean;;;" in vcf
    assert "ORG:ACME SARL" in vcf
    assert "TITLE:Directeur" in vcf
    assert "EMAIL;TYPE=INTERNET,WORK:jean@acme.com" in vcf
    assert "TEL;TYPE=WORK,VOICE:+33123456789" in vcf
    assert "URL:www.acme.com" in vcf
    # Terminaison CRLF (RFC 6350).
    assert "\r\n" in vcf


def test_vcard_escaping():
    contact = Contact(full_name="Doe; John", company="A, B & Co")
    vcf = export.contact_to_vcard(contact)
    assert "\\;" in vcf
    assert "\\," in vcf


def test_vcard_filename_collision(tmp_path):
    contacts = [Contact(full_name="Jean Dupont"), Contact(full_name="Jean Dupont")]
    paths = export.export_vcards(contacts, tmp_path)
    assert len(paths) == 2
    # Les deux fichiers doivent avoir des noms distincts.
    assert paths[0].name != paths[1].name
