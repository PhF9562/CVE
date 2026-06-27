# CardScan — Numérisation de cartes de visite

Application personnelle, simple à utiliser, pour numériser des cartes de visite,
en extraire automatiquement les coordonnées (nom, entreprise, fonction,
téléphone, e-mail…) par OCR, les enregistrer dans un carnet d'adresses local et
les exporter en **JSON** et **vCard (.vcf)**.

## Fonctionnalités

- 📷 **Prendre une photo** d'une carte via la caméra, ou 📂 **importer** un
  fichier JPG, PNG ou PDF.
- 🔎 **OCR automatique** : prétraitement de l'image (niveaux de gris,
  débruitage, correction d'orientation, seuillage adaptatif) puis lecture du
  texte avec Tesseract.
- ✏️ **Validation et édition** : un formulaire affiche les champs détectés, que
  l'utilisateur peut corriger avant de sauvegarder.
- 💾 **Carnet d'adresses local** (SQLite) : consulter, modifier, supprimer et
  rechercher des contacts.
- 📤 **Export en un clic** :
  - *Exporter en JSON* → un fichier `contacts.json` dans le dossier `CV-JSON`.
  - *Exporter en vCard* → un fichier `.vcf` par contact dans le dossier
    `CV-VCF`, compatible Google Contacts, Outlook, Apple Contacts, etc.

## Architecture

Le projet sépare un **cœur sans dépendance** (utilisable et testable partout) des
**couches optionnelles** qui nécessitent des bibliothèques lourdes :

| Module                  | Rôle                                   | Dépendances        |
| ----------------------- | -------------------------------------- | ------------------ |
| `cardscan/contact.py`   | Modèle de données `Contact`            | stdlib             |
| `cardscan/parser.py`    | Analyse du texte OCR → champs          | stdlib             |
| `cardscan/database.py`  | Stockage SQLite (CRUD + recherche)     | stdlib             |
| `cardscan/export.py`    | Export JSON et vCard                   | stdlib             |
| `cardscan/ocr.py`       | Prétraitement image + Tesseract        | opencv, pytesseract, Pillow, pdf2image |
| `cardscan/camera.py`    | Capture webcam                         | opencv             |
| `cardscan/gui.py`       | Interface graphique                    | tkinter            |

Les modules OCR/caméra utilisent des **imports paresseux** : ils s'importent
sans erreur même si OpenCV ou Tesseract sont absents ; l'erreur explicative
n'apparaît qu'au moment d'analyser réellement une carte.

## Installation

```bash
# 1. Dépendances Python
pip install -r requirements.txt

# 2. Dépendances système (OCR)
#    Debian/Ubuntu :
sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils python3-tk
#    macOS (Homebrew) :
brew install tesseract poppler
```

## Utilisation

### Interface graphique

```bash
python -m cardscan
```

1. Cliquer sur **Prendre une photo** ou **Importer un fichier**.
2. Vérifier et corriger les informations détectées.
3. Cliquer sur **Enregistrer**.
4. Utiliser **Exporter en JSON** ou **Exporter en vCard** quand souhaité.
   Les fichiers sont générés dans `~/CardScan/CV-JSON` et `~/CardScan/CV-VCF`.

### Ligne de commande (sans affichage)

```bash
python -m cardscan carte.jpg          # affiche les champs détectés
python -m cardscan carte.jpg --json   # sortie JSON
```

## Tests

Le cœur de l'application est couvert par des tests unitaires ne nécessitant
aucune dépendance externe :

```bash
pip install pytest
pytest
```

## Licence

Voir le fichier [LICENSE](LICENSE).
