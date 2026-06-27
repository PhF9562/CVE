# -*- mode: python ; coding: utf-8 -*-
"""Spécification PyInstaller (API 6.x) pour l'application de numérisation.

Produit un exécutable fenêtré « onefile » :
  - Windows : Numeriseur-Cartes.exe
  - macOS   : Numeriseur-Cartes.app (bundle)

Les bibliothèques OCR sont importées dynamiquement dans ``cartevisite.ocr``
(``__import__``), donc PyInstaller ne les détecte pas tout seul : on les
collecte explicitement via ``collect_all``.
"""

import sys

from PyInstaller.utils.hooks import collect_all

APP_NAME = "Numeriseur-Cartes"

# Sous-modules du paquet (certains importés paresseusement) : on les force.
hiddenimports = [
    "sqlite3",
    "cartevisite",
    "cartevisite.gui",
    "cartevisite.batch",
    "cartevisite.config",
    "cartevisite.ocr",
    "cartevisite.camera",
    "cartevisite.database",
    "cartevisite.export",
    "cartevisite.parser",
    "cartevisite.models",
]
datas = []
binaries = []

# Dépendances OCR importées dynamiquement → collecte exhaustive.
for package in ("cv2", "numpy", "PIL", "pytesseract", "pdf2image"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        # Bibliothèque absente du runner : l'app se dégrade gracieusement.
        pass

a = Analysis(
    ["cartevisite_app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,  # application fenêtrée (pas de terminal)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name=APP_NAME + ".app",
        icon=None,
        bundle_identifier="org.fontayne.numeriseurcartes",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleDisplayName": "Numériseur de cartes",
        },
    )
