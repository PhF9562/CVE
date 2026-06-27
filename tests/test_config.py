"""Tests de la résolution du répertoire de travail (module ``config``)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cartes_visite import config
from cartes_visite.config import EmplacementDonnees


class TestEmplacementDonnees(unittest.TestCase):
    def test_chemins_relatifs_a_la_base(self):
        emp = EmplacementDonnees("/un/dossier")
        self.assertEqual(emp.chemin_db, Path("/un/dossier/contacts.db"))
        self.assertEqual(emp.dossier_json, Path("/un/dossier/CV-JSON"))
        self.assertEqual(emp.dossier_vcf, Path("/un/dossier/CV-VCF"))
        self.assertEqual(emp.chemin_capture, Path("/un/dossier/capture_carte.png"))

    def test_creer_cree_le_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            cible = Path(tmp) / "nouveau"
            emp = EmplacementDonnees(cible).creer()
            self.assertTrue(cible.is_dir())
            self.assertEqual(emp.base, cible)

    def test_expansion_tilde(self):
        emp = EmplacementDonnees("~/cartes")
        self.assertNotIn("~", str(emp.base))


class TestPersistanceConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._config_origine = config.FICHIER_CONFIG
        config.FICHIER_CONFIG = Path(self.tmp.name) / "config.json"

    def tearDown(self):
        config.FICHIER_CONFIG = self._config_origine
        self.tmp.cleanup()

    def test_enregistrer_puis_charger(self):
        self.assertTrue(config.enregistrer_repertoire("/mon/dossier"))
        self.assertEqual(config.charger_repertoire_enregistre(), "/mon/dossier")

    def test_charger_sans_fichier_renvoie_defaut(self):
        self.assertEqual(
            config.charger_repertoire_enregistre(defaut="/x"), "/x"
        )

    def test_resoudre_priorite_argument(self):
        config.enregistrer_repertoire("/dossier/memorise")
        with tempfile.TemporaryDirectory() as tmp:
            emp = config.resoudre_emplacement(tmp)
            self.assertEqual(emp.base, Path(tmp))

    def test_resoudre_utilise_config_si_pas_argument(self):
        cible = Path(self.tmp.name) / "memorise"
        config.enregistrer_repertoire(cible)
        emp = config.resoudre_emplacement(None)
        self.assertEqual(emp.base, cible)
        self.assertTrue(cible.is_dir())


if __name__ == "__main__":
    unittest.main()
