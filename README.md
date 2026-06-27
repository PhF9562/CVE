# CVE — Numériseur de cartes de visite

[![CI](https://github.com/PhF9562/CVE/actions/workflows/ci.yml/badge.svg)](https://github.com/PhF9562/CVE/actions/workflows/ci.yml)

Application personnelle pour **numériser des cartes de visite**, extraire
automatiquement les informations de contact par OCR, les ranger dans un carnet
d'adresses local et les **exporter en JSON et vCard (.vcf)**.

L'application vise un utilisateur non technique : interface épurée, deux boutons
pour scanner, écran de validation des champs détectés, et export en un clic.

## Fonctionnalités

- 📷 **Prendre une photo** (webcam) ou 📂 **importer un fichier** (JPG, PNG, PDF…).
- 🔍 **Prétraitement d'image** (niveaux de gris, débruitage, binarisation,
  correction d'orientation) puis **OCR** via Tesseract.
- 🧠 **Analyse automatique** du texte : nom, entreprise, poste, téléphone,
  e-mail, site web et adresse.
- ✏️ **Validation et édition** des champs avant la sauvegarde.
- 💾 **Carnet d'adresses** local (SQLite) : consulter, modifier, supprimer,
  avec **détection de doublons** par e-mail à l'enregistrement.
- ⬇️ **Export** de tous les contacts :
  - en JSON dans le dossier `CV-JSON/` ;
  - en vCard (un fichier `.vcf` par contact) dans le dossier `CV-VCF/`,
    compatible Google Contacts, Outlook, Apple Contacts, etc.

## Architecture

| Module | Rôle | Dépendances |
|--------|------|-------------|
| `cartes_visite/contact.py`  | Modèle de données `Contact`            | standard |
| `cartes_visite/parser.py`   | Analyse du texte OCR → champs          | standard |
| `cartes_visite/database.py` | Carnet d'adresses SQLite               | standard |
| `cartes_visite/exporter.py` | Export JSON et vCard                    | standard |
| `cartes_visite/ocr.py`      | Prétraitement image + OCR              | OpenCV, Pillow, pytesseract, pdf2image |
| `cartes_visite/app.py`      | Interface graphique tkinter            | tkinter |
| `main.py`                   | Point d'entrée (GUI + ligne de commande) | — |

Le cœur applicatif (modèle, analyse, base, export) ne dépend que de la
**bibliothèque standard de Python** : il reste donc testable et utilisable même
sans les dépendances d'OCR/image.

## Installation

```bash
# 1. Dépendances Python (pour la capture et l'OCR)
pip install -r requirements.txt

# 2. Moteurs système requis par l'OCR
#    Debian/Ubuntu :
sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils
#    macOS (Homebrew) :
brew install tesseract poppler
```

Vérifier que tout est prêt :

```bash
python main.py check
```

## Utilisation

### Interface graphique

```bash
python main.py            # ou : python main.py gui
```

1. Cliquer sur **Prendre une photo** ou **Importer un fichier**.
2. Vérifier et corriger les informations détectées.
3. **Enregistrer** le contact.
4. Utiliser **Exporter en JSON** ou **Exporter en vCard** quand souhaité.

### Ligne de commande (sans interface graphique)

```bash
python main.py scan carte.jpg                 # analyse et affiche les champs
python main.py scan carte.jpg --enregistrer   # analyse et sauvegarde le contact
python main.py export-json                     # exporte le carnet en JSON
python main.py export-vcf                       # exporte le carnet en vCard
```

## Tests

Les tests couvrent l'analyse de texte, la base de données et les exports
(parties indépendantes de l'OCR) :

```bash
python -m unittest discover -s tests
```

## Licence

Voir le fichier [LICENSE](LICENSE).
