# Cadrage_Prototypage — Cadrer un projet décisionnel, puis le maquetter

Deux livrables en un flux, à partir d'un même fichier Excel rempli avec le
client (`Matrice.xlsx`) :

1. **`cadrage.md`** — le **cadrage** consolidé : tous les indicateurs
   (Thèmes › Sujets › KPI), leurs priorités, systèmes/sources de données,
   fiabilités, formules — le périmètre validé avec le client.
2. **`presentation/maquette.html`** — une **maquette web** auto-suffisante qui
   imite fidèlement le langage visuel de Power BI pour valider le contenu du
   futur rapport (navigation, KPIs, visuels) **sur le périmètre retenu**.

> **Maquette HTML, pas Power BI.** Le rendu n'est **pas** un fichier `.pbix`.
> Les chiffres affichés sont **fictifs** (générés sur 2 années closes) : ils
> servent à valider la *forme* du rapport. Les **sources et fiabilités réelles**
> (issues du `Matrice.xlsx`) sont documentées dans `cadrage.md` et signalées
> par un `*` sur la maquette.

## Différence avec le dépôt `Prototypage`

`Prototypage` invente le contenu depuis un questionnaire métier (zéro Excel).
`Cadrage_Prototypage` **part du cadrage** (`Matrice.xlsx` rempli avec le
client) : le périmètre est filtré par priorité, et chaque indicateur porte sa
source et sa fiabilité.

## Prérequis

| Outil | Pourquoi | Installation |
|---|---|---|
| **Node.js 18+** | exécuter opencode + le smoke test | [nodejs.org](https://nodejs.org) |
| **Python 3** | parser le Matrice.xlsx, générer/extraire les données | [python.org](https://python.org) |
| **openpyxl** (Python) | lecture/écriture du `.xlsx` — **bloquant sans lui** | `pip install openpyxl` |
| **opencode** (CLI) | l'agent IA qui pilote le skill | `npm install -g opencode-ai` |
| **Clé de modèle** | ex. OpenRouter (`sk-or-…`) | `opencode auth login` |

## Quickstart

```powershell
pip install openpyxl
opencode
# puis, dans opencode :
> /cadrage MonClient
```

1. **3 fournitures en une question** : déposez le `matrice.xlsx` **rempli avec
   le client** dans `clients/MonClient/matrice.xlsx` + le `logo.png`
   (fond transparent) + la **couleur primaire** (hex, ex. `#00A1B1`).
2. **Question 1 — Périmètre priorité** : `Hautes uniquement (N KPI)` /
   `Hautes + Moyennes (N KPI)` / `Hautes + Moyennes + Basses (N KPI)` — les
   compteurs sont calculés depuis l'Excel.
3. **Question 2 — Proposition globale** : navigation (regroupement des
   Thèmes/Sujets → pages/sous-pages), modèle de données dérivé des Axes et
   Formules, couleurs secondaires. Valider ou ajuster.
4. Ouvrez les livrables : `start clients/MonClient/presentation/maquette.html`
   et lisez `clients/MonClient/cadrage.md` avant de présenter.

## Le fichier `Matrice.xlsx`

Feuille **KPI** (11 colonnes) — remplie par le conseiller **avec** le client :

| Colonne | Rôle |
|---|---|
| Thèmes | Structure de cadrage métier (≠ pages de la maquette) |
| Sujets | Sous-thème (≠ sous-pages) |
| Indicateurs | Le KPI |
| Descriptions | Précision / sous-titre |
| Priorités | `Haute` / `Moyenne` / `Basse` (liste déroulante) — filtre le périmètre |
| Provenance systèmes sources | L'applicatif d'origine des données |
| Sources des données | Table / entrepôt (vide = source non identifiée → fiabilité `Inconnue`) |
| Fiabilités des données | `Fiable` / `Partielle` / `Inconnue` (liste déroulante) — pilote le marqueur `*` |
| Axes d'analyses | Dimensions d'analyse (ex. « par région, par période ») |
| Formules | Sémantique du KPI (ex. `SUM(Montant HT)`) |
| Commentaires | Notes libres |

> Le modèle vierge (`Matrice.xlsx` à la racine) contient déjà les **listes
> déroulantes** Priorités et Fiabilités. Copiez-le dans
> `clients/<client>/matrice.xlsx` et remplissez-le.

## Ce que vous obtenez

- **`cadrage.md`** — synthèse + détail par thème + périmètre maquette +
  alertes fiabilité.
- **`presentation/maquette.html`** — canevas 1920×1080 (16:9), bandeau aux
  couleurs du client, KPIs avec variation N vs N-1, panneau de filtres
  interactif, navigation à deux niveaux, visuels ECharts (courbes, donuts,
  barres, tables).
- **Marqueur de fiabilité** — `*` orange (`Partielle`) ou `◆` rouge
  (`Inconnue`) à côté des KPI/visuels concernés + info-bulle au survol +
  légende dans l'infobulle d'info. `Fiable` n'est pas marqué.
- **`presentation/pitch.md`** — script du conseiller (storytelling + chiffres).

## Dossier client

```
clients/MonClient/
├── matrice.xlsx         ← fourni par vous (cadrage rempli)
├── logo.png             ← fourni par vous (fond transparent)
├── cadrage.json         ← écrit par parse-matrice.py
├── cadrage.md           ← LIVRABLE de cadrage (generate-cadrage.py)
├── CLIENT.md            ← écrit par le skill (marque, couleurs, nav)
├── data-spec.json       ← écrit par le skill (spec des données)
├── donnees.xlsx         ← GÉNÉRÉ par le skill (2 années closes, fictif)
├── nav.json             ← écrit par le skill (navigation + fiabilité)
├── views.json           ← GÉNÉRÉ par build-views.py
└── presentation/
    ├── maquette.html    ← le rendu (marqueurs * inclus)
    └── pitch.md         ← script du conseiller
```

Modèle de départ : `clients/_template/`.

## Garde-fous automatiques

- **Smoke test JS** avant chaque livraison (exit 0 exigé).
- **Données conformes par construction** : auto-contrôle bloquant du générateur.
- **Carte visuelle validée** : `build-views.py` vérifie chaque référence contre
  les données réelles.
- **Contraste WCAG AA** dérivé automatiquement (`--on-primary`).

## Auteur

[agileohdain](https://github.com/agileohdain)
