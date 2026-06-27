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
├── batch.py         # traitement par lots du dossier CV-Scan
└── gui.py           # interface graphique tkinter
tests/               # tests unitaires (parser, base, export, batch)
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

### Traitement par lots d'un dossier (workflow OneDrive)

Organisez votre dossier de travail (par exemple sous
`OneDrive/numérisation`) ainsi :

```
numérisation/
├── CV-Scan/         ← déposez ici les scans à analyser (JPG, PNG, PDF, TIFF, .txt)
│   └── traités/     ← les scans traités avec succès y sont archivés automatiquement
├── CV-VCF/          ← fichiers vCard (.vcf) générés, un par contact
└── CV-JSON/         ← données extraites au format JSON (contacts.json)
```

Lancez l'analyse et l'extraction de tout le dossier `CV-Scan` :

```bash
# Dossier auto-détecté (OneDrive/numérisation ou ./numérisation) :
python -m cartevisite --batch

# …ou dossier explicite :
python -m cartevisite --batch "/chemin/vers/OneDrive/numérisation"

# Options : --lang fra+eng   --no-db (ne pas enregistrer en base)
#           --no-move (ne pas archiver les scans traités)
```

Le dossier peut aussi être imposé via la variable d'environnement
`CV_BASE_DIR`. Depuis l'interface graphique, le bouton **📂 Traiter
CV-Scan** réalise la même opération. Chaque scan illisible est signalé
dans le rapport sans interrompre le lot.

Après un export réussi, chaque scan traité est déplacé dans
`CV-Scan/traités/` : un nouveau passage ne ré-analyse donc que les
nouvelles cartes. Les scans en échec restent en place pour être
retentés. Utilisez `--no-move` pour conserver tous les scans à leur
emplacement.

> Les fichiers `.txt` (texte déjà reconnu) sont acceptés en entrée et
> traités sans Tesseract — pratique pour tester le pipeline.

### Mode console (sans interface)

Analyse rapide d'un fichier et affichage des champs détectés :

```bash
python -m cartevisite --scan chemin/vers/carte.jpg
```

## Tests

```bash
python -m unittest discover -s tests
```

34 tests couvrent le parseur OCR, la base SQLite, les exports et le
traitement par lots du dossier (extraction, archivage, collisions).

## Licence

Voir le fichier [LICENSE](LICENSE).
