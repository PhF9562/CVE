"""Tests de la couche de stockage SQLite."""

import unittest

from cartevisite.database import ContactDatabase
from cartevisite.models import Contact


class TestContactDatabase(unittest.TestCase):
    def setUp(self):
        self.db = ContactDatabase(":memory:")

    def tearDown(self):
        self.db.close()

    def _sample(self, **kw):
        base = dict(full_name="Jean Dupont", company="ACME", email="jean@acme.com", phone="0612345678")
        base.update(kw)
        return Contact(**base)

    def test_add_and_get(self):
        contact = self._sample()
        new_id = self.db.add(contact)
        self.assertIsNotNone(new_id)
        self.assertEqual(contact.id, new_id)

        fetched = self.db.get(new_id)
        self.assertEqual(fetched.full_name, "Jean Dupont")
        self.assertEqual(fetched.email, "jean@acme.com")

    def test_count(self):
        self.assertEqual(self.db.count(), 0)
        self.db.add(self._sample())
        self.db.add(self._sample(full_name="Marie Martin"))
        self.assertEqual(self.db.count(), 2)

    def test_update(self):
        contact = self._sample()
        self.db.add(contact)
        contact.title = "Directeur"
        self.assertTrue(self.db.update(contact))
        self.assertEqual(self.db.get(contact.id).title, "Directeur")

    def test_update_requires_id(self):
        with self.assertRaises(ValueError):
            self.db.update(self._sample())

    def test_delete(self):
        contact = self._sample()
        self.db.add(contact)
        self.assertTrue(self.db.delete(contact.id))
        self.assertIsNone(self.db.get(contact.id))
        self.assertFalse(self.db.delete(contact.id))

    def test_all_sorted(self):
        self.db.add(self._sample(full_name="Zoe"))
        self.db.add(self._sample(full_name="Anna"))
        names = [c.full_name for c in self.db.all()]
        self.assertEqual(names, ["Anna", "Zoe"])

    def test_search(self):
        self.db.add(self._sample(full_name="Jean Dupont", company="ACME"))
        self.db.add(self._sample(full_name="Marie Martin", company="Globex"))
        results = self.db.search("globex")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].full_name, "Marie Martin")


if __name__ == "__main__":
    unittest.main()
