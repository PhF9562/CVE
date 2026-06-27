"""Tests du balayage de répertoires (découverte des fichiers)."""

import pytest

from cardscan.scanner import (
    ScanResult,
    SUPPORTED_EXTENSIONS,
    find_card_files,
    is_supported,
)
from cardscan.contact import Contact


def test_is_supported():
    assert is_supported("carte.jpg")
    assert is_supported("CARTE.PNG")
    assert is_supported("doc.pdf")
    assert not is_supported("notes.txt")
    assert not is_supported("archive.zip")


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def test_find_card_files_filters_extensions(tmp_path):
    _touch(tmp_path / "a.jpg")
    _touch(tmp_path / "b.png")
    _touch(tmp_path / "c.pdf")
    _touch(tmp_path / "notes.txt")
    _touch(tmp_path / "data.csv")

    found = find_card_files(tmp_path)
    names = {p.name for p in found}
    assert names == {"a.jpg", "b.png", "c.pdf"}


def test_find_card_files_recursive(tmp_path):
    _touch(tmp_path / "top.jpg")
    _touch(tmp_path / "sub" / "nested.png")
    _touch(tmp_path / "sub" / "deep" / "card.pdf")

    found = find_card_files(tmp_path, recursive=True)
    names = {p.name for p in found}
    assert names == {"top.jpg", "nested.png", "card.pdf"}


def test_find_card_files_non_recursive(tmp_path):
    _touch(tmp_path / "top.jpg")
    _touch(tmp_path / "sub" / "nested.png")

    found = find_card_files(tmp_path, recursive=False)
    names = {p.name for p in found}
    assert names == {"top.jpg"}


def test_find_card_files_sorted(tmp_path):
    for name in ["z.jpg", "a.jpg", "m.png"]:
        _touch(tmp_path / name)
    found = find_card_files(tmp_path)
    assert found == sorted(found)


def test_find_card_files_empty(tmp_path):
    assert find_card_files(tmp_path) == []


def test_find_card_files_rejects_non_directory(tmp_path):
    f = tmp_path / "a.jpg"
    _touch(f)
    with pytest.raises(NotADirectoryError):
        find_card_files(f)


def test_scan_result_ok_flag():
    ok = ScanResult(path="a.jpg", contact=Contact(full_name="Jean"))
    ko = ScanResult(path="b.jpg", error="illisible")
    assert ok.ok is True
    assert ko.ok is False


def test_supported_extensions_includes_core_formats():
    for ext in (".jpg", ".jpeg", ".png", ".pdf"):
        assert ext in SUPPORTED_EXTENSIONS


def test_scan_directory_isolates_errors(tmp_path, monkeypatch):
    """Un fichier illisible ne fait pas échouer tout le lot."""
    import cardscan.ocr as ocr
    from cardscan.scanner import scan_directory

    _touch(tmp_path / "good.jpg")
    _touch(tmp_path / "bad.png")

    def fake_scan(path, lang="fra+eng"):
        if "bad" in str(path):
            raise ValueError("illisible")
        return Contact(full_name="Jean Dupont", email="jean@acme.com")

    monkeypatch.setattr(ocr, "scan_card", fake_scan)

    results = scan_directory(tmp_path)
    assert len(results) == 2
    ok = [r for r in results if r.ok]
    ko = [r for r in results if not r.ok]
    assert len(ok) == 1 and len(ko) == 1
    assert ko[0].error == "illisible"


def test_cli_directory_scan_saves_and_exports(tmp_path, monkeypatch):
    """Le balayage CLI enregistre les cartes et génère JSON + vCard."""
    import json as _json

    import cardscan.ocr as ocr
    import cardscan.database as database
    from cardscan import export
    from cardscan.__main__ import main

    cards = tmp_path / "cartes"
    cards.mkdir()
    _touch(cards / "a.jpg")
    _touch(cards / "b.png")

    def fake_scan(path, lang="fra+eng"):
        stem = path.stem if hasattr(path, "stem") else str(path)
        return Contact(full_name=f"Contact {stem}", email=f"{stem}@x.com")

    monkeypatch.setattr(ocr, "scan_card", fake_scan)
    # Carnet d'adresses temporaire isolé.
    monkeypatch.setattr(database, "default_db_path", lambda: tmp_path / "test.db")

    rc = main([str(cards), "--export-dir", str(tmp_path)])
    assert rc == 0

    # Carnet : les deux contacts ont été enregistrés.
    db = database.ContactDatabase(tmp_path / "test.db")
    assert db.count() == 2
    db.close()

    # Deux répertoires d'export séparés.
    json_file = tmp_path / export.JSON_DIR_NAME / "contacts.json"
    vcf_dir = tmp_path / export.VCF_DIR_NAME
    assert json_file.exists()
    assert vcf_dir.is_dir()
    data = _json.loads(json_file.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert len(list(vcf_dir.glob("*.vcf"))) == 2
