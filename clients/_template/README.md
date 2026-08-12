# Dossier template

Ce dossier sert de modèle au skill `cadrage-prototypage` : c'est lui qui crée et
remplit `clients/<mon-client>/` pendant la commande `/cadrage <Nom>`.
**Vous n'avez rien à copier ni à éditer à la main.**

Contenu du template :

- `matrice.xlsx` — **modèle vierge** du cadrage (listes déroulantes Priorités +
  Fiabilités). À copier dans `clients/<client>/matrice.xlsx` et remplir avec le
  client.
- `CLIENT.md` — **écrit par le skill** à partir du `matrice.xlsx` et du
  questionnaire guidé (identité, couleurs, contexte & données, cadrage &
  périmètre, arbre de navigation). Vous ne le remplissez pas.
- `cadrage.example.md` — exemple du **livrable de cadrage** (généré par
  `generate-cadrage.py` depuis `cadrage.json`).
- `nav.example.json` — exemple documenté de l'arbre de navigation en
  intentions (écrit par le skill, étendu en `views.json` par
  `scripts/build-views.py`). Inclut le champ `reliability`/`source`.
- `views.json` — schéma de la carte visuelle déclarative (pages → sous-pages →
  KPIs + visuels), **générée mécaniquement** depuis `nav.json`.
- `data-spec.example.json` — exemple documenté du spec de génération des
  données (lu par `scripts/generate-data.py`).
- `bg.svg` (ou `bg.png`) — **optionnel** : image de fond personnalisée
  (~3840×2160). Sa couleur de bandeau **doit valoir** `Primary`.

Procédure complète : voir le README.md à la racine du dépôt.

Fichiers déposés par l'utilisateur (le skill ne les crée jamais) :
- `matrice.xlsx` — le cadrage rempli avec le client
- `logo.png` — le logo du client (fond transparent)

Fichiers produits par le skill (ne pas créer à la main) :
- `cadrage.json` — matrice normalisé (`parse-matrice.py`)
- `cadrage.md` — **livrable de cadrage** (`generate-cadrage.py`)
- `CLIENT.md` et `data-spec.json` — écrits après le questionnaire guidé
- `donnees.xlsx` — **données fictives générées** (2 années civiles closes)
- `nav.json` — arbre de navigation validé (intentions courtes + fiabilité)
- `views.json` — carte visuelle **générée par `build-views.py`** depuis
  `nav.json` (validée contre les données réelles)
- `presentation/maquette.html` — la maquette, **interactive** : panneau de
  filtres fonctionnel, KPIs avec **variation vs N-1**, et **marqueurs `*` de
  fiabilité** (orange = partielle, rouge = source inconnue) + légende pied de
  page.
- `presentation/pitch.md` — **script du conseiller** (storytelling + chiffres
  réels), généré par `generate-pitch.py` à la fin de la Phase 3.
