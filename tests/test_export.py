"""Tests de l'export JSON et vCard."""

import json

from cartedevisite.export import contact_to_vcard, export_json, export_vcards
from cartedevisite.models import Contact


def _sample():
    return Contact(
        name="Jean Dupont",
        company="Mega Corp",
        title="Directeur",
        phone="+33 1 23 45 67 89",
        email="jean@megacorp.fr",
        website="www.megacorp.fr",
    )


def test_vcard_contains_mandatory_fields():
    card = contact_to_vcard(_sample())
    assert card.startswith("BEGIN:VCARD")
    assert "VERSION:3.0" in card
    assert "FN:Jean Dupont" in card
    assert "N:Dupont;Jean;;;" in card
    assert "ORG:Mega Corp" in card
    assert "EMAIL;TYPE=WORK:jean@megacorp.fr" in card
    assert card.rstrip().endswith("END:VCARD")


def test_vcard_fallback_fullname_when_no_name():
    card = contact_to_vcard(Contact(email="x@y.com"))
    assert "FN:x@y.com" in card


def test_vcard_escapes_special_chars():
    card = contact_to_vcard(Contact(name="Doe", company="A, B; C"))
    assert "ORG:A\\, B\\; C" in card


def test_export_json_roundtrip(tmp_path):
    path = export_json([_sample()], tmp_path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["name"] == "Jean Dupont"
    assert "id" not in data[0]  # l'id ne doit pas être exporté


def test_export_vcards_one_file_per_contact(tmp_path):
    contacts = [Contact(name="Alice Martin"), Contact(name="Bob Durand")]
    paths = export_vcards(contacts, tmp_path)
    assert len(paths) == 2
    assert all(p.suffix == ".vcf" and p.exists() for p in paths)


def test_export_vcards_unique_filenames_on_collision(tmp_path):
    contacts = [Contact(name="Jean Dupont"), Contact(name="Jean Dupont")]
    paths = export_vcards(contacts, tmp_path)
    assert len({p.name for p in paths}) == 2
