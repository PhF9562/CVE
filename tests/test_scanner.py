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
