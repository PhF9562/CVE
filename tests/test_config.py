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


class TestDetectionOneDrive(unittest.TestCase):
    def setUp(self):
        # Isole les variables d'environnement OneDrive pendant les tests.
        self._sauvegarde = {
            k: os.environ.pop(k, None)
            for k in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")
        }

    def tearDown(self):
        for k, v in self._sauvegarde.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def test_detecte_via_variable_environnement(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["OneDrive"] = tmp
            self.assertEqual(config.detecter_onedrive(), Path(tmp))

    def test_variable_pointant_vers_dossier_inexistant_ignoree(self):
        os.environ["OneDrive"] = "/chemin/qui/n/existe/pas"
        # Sans dossier ~/OneDrive non plus, doit retourner None ou un vrai dossier.
        resultat = config.detecter_onedrive()
        self.assertNotEqual(resultat, Path("/chemin/qui/n/existe/pas"))

    def test_defaut_utilise_onedrive_et_sous_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["OneDrive"] = tmp
            defaut = config.repertoire_par_defaut()
            self.assertEqual(defaut, Path(tmp) / config.NOM_SOUS_DOSSIER)

    def test_defaut_sans_onedrive_retombe_sur_accueil(self):
        # Aucune variable, et on suppose l'absence de ~/OneDrive en CI.
        defaut = config.repertoire_par_defaut()
        self.assertEqual(defaut.name, config.NOM_SOUS_DOSSIER)


if __name__ == "__main__":
    unittest.main()
