"""Tests des exports JSON et vCard (module ``exporter``)."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cartes_visite.contact import Contact
from cartes_visite import exporter


class TestExport(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.contacts = [
            Contact(id=1, nom="Marie Dupont", entreprise="ACME", poste="Directrice",
                    telephone="+33123456789", email="marie@acme.fr",
                    site_web="www.acme.fr", adresse="12 rue de la Paix, Paris"),
            Contact(id=2, nom="Jean Martin", email="jean@x.fr"),
        ]

    def test_export_json(self):
        cible = exporter.exporter_json(self.contacts, dossier=self.dossier)
        self.assertTrue(cible.exists())
        donnees = json.loads(cible.read_text(encoding="utf-8"))
        self.assertEqual(len(donnees), 2)
        self.assertEqual(donnees[0]["nom"], "Marie Dupont")
        self.assertEqual(donnees[0]["email"], "marie@acme.fr")

    def test_export_vcards(self):
        chemins = exporter.exporter_vcards(self.contacts, dossier=self.dossier)
        self.assertEqual(len(chemins), 2)
        contenu = chemins[0].read_text(encoding="utf-8")
        self.assertIn("BEGIN:VCARD", contenu)
        self.assertIn("VERSION:3.0", contenu)
        self.assertIn("FN:Marie Dupont", contenu)
        self.assertIn("ORG:ACME", contenu)
        self.assertIn("TEL", contenu)
        self.assertIn("EMAIL", contenu)
        self.assertIn("END:VCARD", contenu)
        # La vCard générée se termine par CRLF (vérifié sur la chaîne produite,
        # avant la conversion universelle des fins de ligne à la relecture).
        self.assertTrue(
            exporter.contact_vers_vcard(self.contacts[0]).endswith("\r\n")
        )

    def test_vcard_echappement(self):
        c = Contact(nom="Test", entreprise="A; B, C")
        vcf = exporter.contact_vers_vcard(c)
        self.assertIn("ORG:A\\; B\\, C", vcf)

    def test_noms_fichiers_uniques(self):
        memes = [Contact(nom="Dupont"), Contact(nom="Dupont")]
        chemins = exporter.exporter_vcards(memes, dossier=self.dossier)
        self.assertEqual(len({c.name for c in chemins}), 2)


if __name__ == "__main__":
    unittest.main()
