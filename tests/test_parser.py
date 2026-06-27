"""Tests de l'analyse de texte OCR (module ``parser``)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cartes_visite.parser import analyser_texte


class TestAnalyseTexte(unittest.TestCase):
    def test_carte_complete(self):
        texte = """
        Marie Dupont
        Directrice Marketing
        ACME Solutions SARL
        12 rue de la Paix, 75002 Paris
        Tel : +33 1 23 45 67 89
        marie.dupont@acme.fr
        www.acme.fr
        """
        c = analyser_texte(texte)
        self.assertEqual(c.email, "marie.dupont@acme.fr")
        self.assertEqual(c.telephone, "+33123456789")
        self.assertIn("acme", c.site_web.lower())
        self.assertIn("Directrice", c.poste)
        self.assertIn("ACME", c.entreprise)
        self.assertEqual(c.nom, "Marie Dupont")
        self.assertIn("Paris", c.adresse)

    def test_email_seul(self):
        c = analyser_texte("contact@exemple.com")
        self.assertEqual(c.email, "contact@exemple.com")

    def test_telephone_formats_varies(self):
        for brut, attendu in [
            ("01.23.45.67.89", "0123456789"),
            ("(0)1 23 45 67 89", "0123456789"),
            ("+33 6 12 34 56 78", "+33612345678"),
        ]:
            c = analyser_texte(f"Tel: {brut}")
            self.assertEqual(c.telephone, attendu, brut)

    def test_ne_confond_pas_domaine_email_et_site(self):
        c = analyser_texte("jean@société.com")
        self.assertEqual(c.email, "jean@société.com")
        self.assertEqual(c.site_web, "")

    def test_poste_reconnu_par_mot_cle(self):
        c = analyser_texte("Jean Martin\nIngénieur logiciel\nTechCorp Inc")
        self.assertIn("Ingénieur", c.poste)
        self.assertIn("TechCorp", c.entreprise)
        self.assertEqual(c.nom, "Jean Martin")

    def test_texte_vide(self):
        c = analyser_texte("")
        self.assertTrue(c.est_vide())


if __name__ == "__main__":
    unittest.main()
