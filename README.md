# CVE — Numériseur de cartes de visite

Application personnelle de numérisation de cartes de visite. Elle combine
une interface graphique intuitive (tkinter) et un traitement OCR en
arrière-plan pour extraire automatiquement les informations de contact à
partir de photos ou de scans (JPG, PNG, PDF), les stocker dans un carnet
d'adresses local, puis les exporter en **JSON** et **vCard (.vcf)**.

## Fonctionnalités

- 📷 **Prendre une photo** d'une carte via la webcam, ou 📁 **importer**
  un fichier image / PDF existant.
- 🔍 **OCR automatique** (Tesseract) avec prétraitement d'image (niveaux
  de gris, débruitage, binarisation adaptative) via OpenCV.
- 🧠 **Extraction des champs** : nom, fonction, entreprise, téléphone,
  e-mail, site web — par expressions régulières et heuristiques.
- ✅ **Écran de validation** : chaque champ détecté peut être corrigé
  avant la sauvegarde.
- 💾 **Carnet d'adresses local** (SQLite) : consulter, modifier, supprimer.
- 📤 **Export en un clic** :
  - JSON → dossier `CV-JSON/contacts.json` ;
  - vCard → un fichier `.vcf` par contact dans `CV-VCF/` (compatible
    Google Contacts, Outlook, Apple Contacts).

## Architecture

```
cartevisite/
├── __init__.py      # paquet + version
├── __main__.py      # point d'entrée (GUI ou mode console --scan)
├── models.py        # dataclass Contact (sérialisation, affichage)
├── parser.py        # extraction des champs depuis le texte OCR
├── ocr.py           # prétraitement image + OCR (OpenCV / pytesseract)
├── camera.py        # capture webcam (OpenCV)
├── database.py      # stockage SQLite (CRUD + recherche)
├── export.py        # export JSON et vCard 3.0
└── gui.py           # interface graphique tkinter
tests/               # tests unitaires (parser, base, export)
```

Le **cœur métier** (`models`, `parser`, `database`, `export`) ne dépend
d'aucune bibliothèque externe : il est entièrement testable sans
Tesseract, sans OpenCV et sans serveur d'affichage. Les dépendances
« lourdes » sont importées paresseusement ; en leur absence, l'OCR lève
une erreur explicite et l'interface propose la saisie manuelle.

## Installation

```bash
# 1) Dépendances Python (OCR)
pip install -r requirements.txt

# 2) Moteur Tesseract + poppler (pour les PDF), exemples :
#    Debian/Ubuntu :
sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils
#    macOS (Homebrew) :
brew install tesseract poppler
```

> `tkinter` est fourni avec la plupart des distributions Python. Sur
> Debian/Ubuntu : `sudo apt install python3-tk`.

## Utilisation

### Interface graphique

```bash
python -m cartevisite
# Options : --db contacts.db  --export-dir .
```

1. Cliquez sur **Prendre une photo** ou **Importer un fichier**.
2. Vérifiez et corrigez les informations détectées, puis **Enregistrez**.
3. Quand vous le souhaitez, **Exportez en JSON** ou **en vCard**.

### Mode console (sans interface)

Analyse rapide d'un fichier et affichage des champs détectés :

```bash
python -m cartevisite --scan chemin/vers/carte.jpg
```

## Tests

```bash
python -m unittest discover -s tests
```

24 tests couvrent le parseur OCR, la base SQLite et les exports.

## Licence

Voir le fichier [LICENSE](LICENSE).
