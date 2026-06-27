# CVE — Numériseur de cartes de visite

Application personnelle de **numérisation de cartes de visite**. Elle extrait
automatiquement les coordonnées (nom, société, fonction, téléphone, e-mail,
site web) à partir d'une photo ou d'un scan, les enregistre dans un carnet
d'adresses local, et permet de les exporter au format **JSON** et **vCard
(.vcf)**.

## Fonctionnalités

- 📷 **Prendre une photo** d'une carte via la webcam, ou 📂 **importer** un
  fichier `JPG`, `PNG` ou `PDF`.
- 🔎 **OCR** automatique (Tesseract) après prétraitement de l'image
  (niveaux de gris, redressement, binarisation).
- ✏️ **Écran de validation** : les champs détectés sont pré-remplis et
  modifiables avant l'enregistrement.
- 🗂️ **Carnet d'adresses local** (SQLite) : consulter, rechercher, modifier
  et supprimer les contacts.
- 📤 **Export en un clic** :
  - JSON dans le dossier `CV-JSON/`
  - une vCard `.vcf` par contact dans `CV-VCF/` (compatible Google Contacts,
    Outlook, Apple Contacts…).

## Architecture

La logique métier est découplée des dépendances lourdes (OpenCV, Tesseract,
tkinter), ce qui la rend testable et utilisable sans elles.

| Module | Rôle |
| --- | --- |
| `cartedevisite/models.py`   | Modèle `Contact` (dataclass). |
| `cartedevisite/parser.py`   | Analyse du texte OCR → champs de contact. |
| `cartedevisite/database.py` | Stockage SQLite (CRUD, recherche). |
| `cartedevisite/export.py`   | Export JSON et vCard 3.0. |
| `cartedevisite/ocr.py`      | Prétraitement image + OCR (imports paresseux). |
| `cartedevisite/gui.py`      | Interface graphique tkinter. |
| `cartedevisite/cli.py`      | Ligne de commande (mode sans écran). |

## Installation

```bash
# Dépendances système (Debian/Ubuntu)
sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils python3-tk

# Dépendances Python
pip install -r requirements.txt
```

> Le cœur de l'application (base de données, analyse, export) fonctionne sans
> aucune dépendance externe. Les paquets du `requirements.txt` ne sont
> nécessaires que pour numériser réellement des images/PDF et afficher la
> caméra.

## Utilisation

### Interface graphique

```bash
python main.py
```

### Ligne de commande

```bash
python main.py scan carte.jpg     # numérise et enregistre une carte
python main.py list               # liste les contacts
python main.py export json        # exporte en JSON (dossier CV-JSON/)
python main.py export vcard       # exporte en vCard (dossier CV-VCF/)
python main.py export all         # les deux formats
```

## Emplacement des données

Les contacts et les exports sont stockés dans le dossier de données de
l'utilisateur (par défaut `~/.local/share/CarteDeVisite` sous Linux). On peut
le redéfinir via la variable d'environnement `CARTEDEVISITE_HOME` :

```bash
CARTEDEVISITE_HOME=./mes-cartes python main.py list
```

## Tests

```bash
pip install pytest
python -m pytest
```

## Licence

Voir le fichier [LICENSE](LICENSE).
