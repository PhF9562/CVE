"""Tests du carnet d'adresses SQLite (module ``database``)."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cartes_visite.contact import Contact
from cartes_visite.database import CarnetAdresses


class TestCarnetAdresses(unittest.TestCase):
    def setUp(self):
        self.fichier = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.fichier.close()
        self.carnet = CarnetAdresses(self.fichier.name)

    def tearDown(self):
        self.carnet.fermer()
        os.unlink(self.fichier.name)

    def test_ajout_et_lecture(self):
        c = Contact(nom="Alice", email="alice@x.fr")
        cid = self.carnet.ajouter(c)
        self.assertIsNotNone(cid)
        relu = self.carnet.obtenir(cid)
        self.assertEqual(relu.nom, "Alice")
        self.assertEqual(relu.email, "alice@x.fr")

    def test_modification(self):
        c = Contact(nom="Bob")
        self.carnet.ajouter(c)
        c.entreprise = "Globex"
        self.carnet.modifier(c)
        self.assertEqual(self.carnet.obtenir(c.id).entreprise, "Globex")

    def test_enregistrer_insere_puis_met_a_jour(self):
        c = Contact(nom="Carol")
        cid = self.carnet.enregistrer(c)
        self.assertEqual(self.carnet.nombre(), 1)
        c.poste = "CEO"
        self.assertEqual(self.carnet.enregistrer(c), cid)
        self.assertEqual(self.carnet.nombre(), 1)
        self.assertEqual(self.carnet.obtenir(cid).poste, "CEO")

    def test_suppression(self):
        c = Contact(nom="Dan")
        self.carnet.ajouter(c)
        self.carnet.supprimer(c.id)
        self.assertIsNone(self.carnet.obtenir(c.id))
        self.assertEqual(self.carnet.nombre(), 0)

    def test_recherche(self):
        self.carnet.ajouter(Contact(nom="Eve", entreprise="Initech"))
        self.carnet.ajouter(Contact(nom="Frank", entreprise="Umbrella"))
        resultats = self.carnet.rechercher("Initech")
        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0].nom, "Eve")


if __name__ == "__main__":
    unittest.main()
