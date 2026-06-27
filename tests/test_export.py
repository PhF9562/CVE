"""Tests des exports JSON et vCard."""

import json
import tempfile
import unittest
from pathlib import Path

from cartevisite.export import (
    contact_to_vcard,
    contacts_to_json,
    export_json,
    export_vcards,
)
from cartevisite.models import Contact


def _sample():
    return Contact(
        full_name="Jean Dupont",
        company="ACME SARL",
        title="Directeur",
        phone="+33612345678",
        email="jean@acme.com",
        website="www.acme.com",
        address="1 rue de Paris, 75001 Paris",
    )


class TestJsonExport(unittest.TestCase):
    def test_contacts_to_json_roundtrip(self):
        data = json.loads(contacts_to_json([_sample()]))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["email"], "jean@acme.com")
        self.assertNotIn("id", data[0])

    def test_export_json_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = export_json([_sample()], tmp)
            self.assertTrue(path.exists())
            self.assertEqual(path.parent.name, "CV-JSON")
            content = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(content[0]["company"], "ACME SARL")


class TestVCardExport(unittest.TestCase):
    def test_vcard_structure(self):
        card = contact_to_vcard(_sample())
        self.assertIn("BEGIN:VCARD", card)
        self.assertIn("VERSION:3.0", card)
        self.assertIn("FN:Jean Dupont", card)
        self.assertIn("N:Dupont;Jean;;;", card)
        self.assertIn("ORG:ACME SARL", card)
        self.assertIn("TITLE:Directeur", card)
        self.assertIn("TEL;TYPE=WORK,VOICE:+33612345678", card)
        self.assertIn("EMAIL;TYPE=WORK:jean@acme.com", card)
        self.assertIn("END:VCARD", card)
        self.assertTrue(card.endswith("\r\n"))

    def test_vcard_escaping(self):
        card = contact_to_vcard(Contact(full_name="A", company="Smith, Jones & Co; Ltd"))
        self.assertIn("ORG:Smith\\, Jones & Co\\; Ltd", card)

    def test_export_vcards_one_file_per_contact(self):
        contacts = [_sample(), Contact(full_name="Marie Martin")]
        with tempfile.TemporaryDirectory() as tmp:
            paths = export_vcards(contacts, tmp)
            self.assertEqual(len(paths), 2)
            self.assertTrue(all(p.suffix == ".vcf" for p in paths))
            self.assertEqual(paths[0].parent.name, "CV-VCF")

    def test_export_vcards_unique_filenames(self):
        contacts = [Contact(full_name="Jean Dupont"), Contact(full_name="Jean Dupont")]
        with tempfile.TemporaryDirectory() as tmp:
            paths = export_vcards(contacts, tmp)
            self.assertEqual(len({p.name for p in paths}), 2)


if __name__ == "__main__":
    unittest.main()
