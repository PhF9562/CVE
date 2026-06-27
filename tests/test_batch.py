"""Tests du traitement par lots du dossier CV-Scan."""

import json
import tempfile
import unittest
from pathlib import Path

from cartevisite.batch import ensure_layout, find_base_dir, list_scans, process_directory

CARD_A = (
    "Jean Dupont\n"
    "Directeur Commercial\n"
    "ACME SARL\n"
    "Tel: +33 6 12 34 56 78\n"
    "jean.dupont@acme.com\n"
    "www.acme.com\n"
)
CARD_B = (
    "Marie Martin\n"
    "Responsable Marketing\n"
    "GLOBEX\n"
    "06 98 76 54 32\n"
    "marie@globex.io\n"
)


def _make_tree(tmp: str):
    base = Path(tmp) / "numérisation"
    ensure_layout(base)
    (base / "CV-Scan" / "carte_a.txt").write_text(CARD_A, encoding="utf-8")
    (base / "CV-Scan" / "carte_b.txt").write_text(CARD_B, encoding="utf-8")
    return base


class TestLayout(unittest.TestCase):
    def test_ensure_layout_creates_subdirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "numérisation"
            ensure_layout(base)
            for sub in ("CV-Scan", "CV-VCF", "CV-JSON"):
                self.assertTrue((base / sub).is_dir())

    def test_find_base_dir_explicit(self):
        self.assertEqual(find_base_dir("/x/y/numérisation"), Path("/x/y/numérisation"))

    def test_list_scans_filters_and_sorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _make_tree(tmp)
            (base / "CV-Scan" / "ignore.docx").write_text("x", encoding="utf-8")
            names = [p.name for p in list_scans(base)]
            self.assertEqual(names, ["carte_a.txt", "carte_b.txt"])


class TestProcessDirectory(unittest.TestCase):
    def test_full_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _make_tree(tmp)
            result = process_directory(base_dir=base, log=lambda *_: None)

            self.assertEqual(len(result.contacts), 2)
            self.assertEqual(len(result.failures), 0)

            # JSON exporté et bien formé.
            self.assertTrue(result.json_path.exists())
            self.assertEqual(result.json_path.parent.name, "CV-JSON")
            data = json.loads(result.json_path.read_text(encoding="utf-8"))
            emails = sorted(c["email"] for c in data)
            self.assertEqual(emails, ["jean.dupont@acme.com", "marie@globex.io"])

            # Un fichier vCard par contact dans CV-VCF.
            self.assertEqual(len(result.vcf_paths), 2)
            for p in result.vcf_paths:
                self.assertEqual(p.parent.name, "CV-VCF")
                self.assertIn("BEGIN:VCARD", p.read_text(encoding="utf-8"))

    def test_batch_with_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _make_tree(tmp)
            db_path = Path(tmp) / "contacts.db"
            process_directory(base_dir=base, db_path=db_path, log=lambda *_: None)

            from cartevisite.database import ContactDatabase
            with ContactDatabase(db_path) as db:
                self.assertEqual(db.count(), 2)

    def test_processed_files_are_moved(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _make_tree(tmp)
            result = process_directory(base_dir=base, log=lambda *_: None)

            scan_dir = base / "CV-Scan"
            processed = scan_dir / "traités"
            # Les deux scans réussis sont déplacés…
            self.assertEqual(len(result.moved_files), 2)
            self.assertTrue((processed / "carte_a.txt").exists())
            self.assertTrue((processed / "carte_b.txt").exists())
            # …et ne sont plus à la racine de CV-Scan.
            self.assertFalse((scan_dir / "carte_a.txt").exists())
            self.assertFalse((scan_dir / "carte_b.txt").exists())
            # Un second passage ne trouve plus rien à traiter.
            again = process_directory(base_dir=base, log=lambda *_: None)
            self.assertEqual(again.contacts, [])

    def test_no_move_keeps_scans(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _make_tree(tmp)
            process_directory(base_dir=base, move_processed=False, log=lambda *_: None)
            self.assertTrue((base / "CV-Scan" / "carte_a.txt").exists())
            self.assertFalse((base / "CV-Scan" / "traités").exists())

    def test_failed_scan_not_moved(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _make_tree(tmp)
            # Un scan vide ne produit aucun contact : il reste en place.
            (base / "CV-Scan" / "vide.txt").write_text("   \n", encoding="utf-8")
            process_directory(base_dir=base, log=lambda *_: None)
            self.assertTrue((base / "CV-Scan" / "vide.txt").exists())
            self.assertFalse((base / "CV-Scan" / "traités" / "vide.txt").exists())

    def test_move_handles_name_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _make_tree(tmp)
            # Pré-remplit traités/ avec un fichier homonyme.
            processed = base / "CV-Scan" / "traités"
            processed.mkdir(parents=True, exist_ok=True)
            (processed / "carte_a.txt").write_text("ancien", encoding="utf-8")
            process_directory(base_dir=base, log=lambda *_: None)
            # L'ancien fichier est préservé, le nouveau est suffixé.
            self.assertEqual((processed / "carte_a.txt").read_text(encoding="utf-8"), "ancien")
            self.assertTrue((processed / "carte_a_2.txt").exists())

    def test_json_is_cumulative_across_runs(self):
        # Régression : avec archivage des scans, contacts.json doit cumuler
        # les contacts de tous les passages, pas seulement du dernier.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "numérisation"
            ensure_layout(base)
            db_path = Path(tmp) / "contacts.db"

            (base / "CV-Scan" / "c1.txt").write_text(CARD_A, encoding="utf-8")
            process_directory(base_dir=base, db_path=db_path, log=lambda *_: None)

            (base / "CV-Scan" / "c2.txt").write_text(CARD_B, encoding="utf-8")
            result = process_directory(base_dir=base, db_path=db_path, log=lambda *_: None)

            data = json.loads(result.json_path.read_text(encoding="utf-8"))
            emails = sorted(c["email"] for c in data)
            self.assertEqual(emails, ["jean.dupont@acme.com", "marie@globex.io"])
            # Un fichier vCard par contact cumulé.
            self.assertEqual(len(list((base / "CV-VCF").glob("*.vcf"))), 2)

    def test_name_fallback_skips_phone_line(self):
        from cartevisite.parser import parse_contact
        contact = parse_contact("mobile: 06 12 34 56 78\njean@acme.com")
        self.assertNotIn("06", contact.full_name)

    def test_empty_scan_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "numérisation"
            ensure_layout(base)
            result = process_directory(base_dir=base, log=lambda *_: None)
            self.assertEqual(result.contacts, [])
            self.assertIsNone(result.json_path)


if __name__ == "__main__":
    unittest.main()
