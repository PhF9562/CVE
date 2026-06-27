"""Tests des préférences persistantes et de leur intégration au batch."""

import os
import tempfile
import unittest
from pathlib import Path

from cartevisite import config


class _ConfigEnv(unittest.TestCase):
    """Isole CARTEVISITE_CONFIG dans un fichier temporaire par test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cfg = Path(self._tmp.name) / "config.json"
        self._prev = os.environ.get("CARTEVISITE_CONFIG")
        os.environ["CARTEVISITE_CONFIG"] = str(self._cfg)

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("CARTEVISITE_CONFIG", None)
        else:
            os.environ["CARTEVISITE_CONFIG"] = self._prev
        self._tmp.cleanup()


class TestConfig(_ConfigEnv):
    def test_empty_when_absent(self):
        self.assertEqual(config.load_config(), {})
        self.assertIsNone(config.get_base_dir())

    def test_set_and_get_base_dir(self):
        config.set_base_dir("/data/numérisation")
        self.assertEqual(config.get_base_dir(), Path("/data/numérisation"))
        # Persisté sur le disque et relu indépendamment.
        self.assertTrue(self._cfg.is_file())
        self.assertEqual(config.load_config()["base_dir"], "/data/numérisation")

    def test_corrupt_config_is_ignored(self):
        self._cfg.write_text("{ pas du json", encoding="utf-8")
        self.assertEqual(config.load_config(), {})
        self.assertIsNone(config.get_base_dir())

    def test_set_base_dir_preserves_other_keys(self):
        config.save_config({"autre": 42})
        config.set_base_dir("/x/numérisation")
        cfg = config.load_config()
        self.assertEqual(cfg["autre"], 42)
        self.assertEqual(cfg["base_dir"], "/x/numérisation")


class TestFindBaseDirUsesConfig(_ConfigEnv):
    def test_config_wins_over_autodetect(self):
        from cartevisite.batch import find_base_dir

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "mon-dossier"
            config.set_base_dir(target)
            # Sans argument ni CV_BASE_DIR, c'est le dossier mémorisé qui gagne.
            self.assertEqual(find_base_dir(), target)

    def test_explicit_wins_over_config(self):
        from cartevisite.batch import find_base_dir

        config.set_base_dir("/data/numérisation")
        self.assertEqual(find_base_dir("/autre/chemin"), Path("/autre/chemin"))

    def test_env_wins_over_config(self):
        from cartevisite.batch import find_base_dir

        config.set_base_dir("/data/numérisation")
        prev = os.environ.get("CV_BASE_DIR")
        os.environ["CV_BASE_DIR"] = "/env/chemin"
        try:
            self.assertEqual(find_base_dir(), Path("/env/chemin"))
        finally:
            if prev is None:
                os.environ.pop("CV_BASE_DIR", None)
            else:
                os.environ["CV_BASE_DIR"] = prev


if __name__ == "__main__":
    unittest.main()
