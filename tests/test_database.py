"""Tests de la couche de stockage SQLite."""

from cardscan.contact import Contact
from cardscan.database import ContactDatabase


def make_db():
    return ContactDatabase(":memory:")


def test_add_and_get():
    db = make_db()
    c = Contact(full_name="Jean Dupont", email="jean@acme.com")
    cid = db.add(c)
    assert cid is not None and c.id == cid
    fetched = db.get(cid)
    assert fetched.full_name == "Jean Dupont"
    assert fetched.email == "jean@acme.com"
    db.close()


def test_update():
    db = make_db()
    c = Contact(full_name="Marie", phone="0102030405")
    db.add(c)
    c.phone = "0607080910"
    db.update(c)
    assert db.get(c.id).phone == "0607080910"
    db.close()


def test_delete():
    db = make_db()
    c = Contact(full_name="A supprimer")
    db.add(c)
    assert db.count() == 1
    db.delete(c.id)
    assert db.count() == 0
    assert db.get(c.id) is None
    db.close()


def test_all_sorted_by_name():
    db = make_db()
    db.add(Contact(full_name="Zoé"))
    db.add(Contact(full_name="Alice"))
    names = [c.full_name for c in db.all()]
    assert names == ["Alice", "Zoé"]
    db.close()


def test_search():
    db = make_db()
    db.add(Contact(full_name="Jean Dupont", company="ACME"))
    db.add(Contact(full_name="Marie Curie", company="Radium"))
    results = db.search("acme")
    assert len(results) == 1
    assert results[0].full_name == "Jean Dupont"
    db.close()


def test_update_without_id_raises():
    db = make_db()
    try:
        db.update(Contact(full_name="Sans id"))
        assert False, "doit lever ValueError"
    except ValueError:
        pass
    db.close()
