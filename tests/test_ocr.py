"""Tests des utilitaires OCR ne nécessitant pas les dépendances d'image."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cartes_visite import ocr
from cartes_visite.config import EmplacementDonnees


class TestListerFichiersAAnalyser(unittest.TestCase):
    def test_filtre_extensions_et_tri(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "b.png").write_bytes(b"x")
            (base / "a.jpg").write_bytes(b"x")
            (base / "doc.pdf").write_bytes(b"x")
            (base / "notes.txt").write_bytes(b"x")        # ignoré (extension)
            (base / ".cache.png").write_bytes(b"x")        # ignoré (caché)
            (base / "sous-dossier").mkdir()                # ignoré (dossier)

            fichiers = ocr.lister_fichiers_a_analyser(base)
            noms = [f.name for f in fichiers]
            self.assertEqual(noms, ["a.jpg", "b.png", "doc.pdf"])

    def test_dossier_inexistant(self):
        self.assertEqual(ocr.lister_fichiers_a_analyser("/n/existe/pas"), [])


class TestDossiersEmplacement(unittest.TestCase):
    def test_creer_cree_le_dossier_entree(self):
        with tempfile.TemporaryDirectory() as tmp:
            emp = EmplacementDonnees(Path(tmp) / "wd").creer()
            self.assertTrue(emp.dossier_entree.is_dir())
            self.assertEqual(emp.dossier_entree.name, "à analyser")
            self.assertEqual(emp.dossier_traites.name, "analysés")


if __name__ == "__main__":
    unittest.main()
