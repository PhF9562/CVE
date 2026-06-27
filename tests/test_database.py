"""Tests de la couche de stockage SQLite."""

from cartedevisite.database import ContactDatabase
from cartedevisite.models import Contact


def _db(tmp_path):
    return ContactDatabase(tmp_path / "contacts.db")


def test_add_and_get(tmp_path):
    with _db(tmp_path) as db:
        contact = Contact(name="Jean Dupont", email="jean@x.fr")
        cid = db.add(contact)
        assert cid == contact.id
        fetched = db.get(cid)
        assert fetched.name == "Jean Dupont"
        assert fetched.email == "jean@x.fr"


def test_update(tmp_path):
    with _db(tmp_path) as db:
        contact = Contact(name="Jean")
        db.add(contact)
        contact.name = "Jean Dupont"
        contact.phone = "0102030405"
        db.update(contact)
        assert db.get(contact.id).name == "Jean Dupont"
        assert db.get(contact.id).phone == "0102030405"


def test_delete(tmp_path):
    with _db(tmp_path) as db:
        cid = db.add(Contact(name="A"))
        db.delete(cid)
        assert db.get(cid) is None
        assert db.count() == 0


def test_all_sorted_by_name(tmp_path):
    with _db(tmp_path) as db:
        db.add(Contact(name="Zoé"))
        db.add(Contact(name="Alice"))
        names = [c.name for c in db.all()]
        assert names == ["Alice", "Zoé"]


def test_search(tmp_path):
    with _db(tmp_path) as db:
        db.add(Contact(name="Jean Dupont", company="ACME"))
        db.add(Contact(name="Marie Curie", company="Labo"))
        assert len(db.search("ACME")) == 1
        assert db.search("ACME")[0].name == "Jean Dupont"
        assert len(db.search("introuvable")) == 0


def test_count_and_add_many(tmp_path):
    with _db(tmp_path) as db:
        ids = db.add_many([Contact(name="A"), Contact(name="B"), Contact(name="C")])
        assert len(ids) == 3
        assert db.count() == 3


def test_persistence_across_connections(tmp_path):
    path = tmp_path / "contacts.db"
    db1 = ContactDatabase(path)
    db1.add(Contact(name="Persistant"))
    db1.close()

    db2 = ContactDatabase(path)
    assert db2.count() == 1
    assert db2.all()[0].name == "Persistant"
    db2.close()
