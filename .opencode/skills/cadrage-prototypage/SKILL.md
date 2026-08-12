# Skill: cadrage-prototypage

## Ce que je fais
Je **cadre** un projet décisionnel à partir d'un fichier Excel rempli avec le
client (`matrice.xlsx`), puis je produis une **maquette** de dashboard Power BI
en HTML auto-suffisant (canevas 16:9, bandeau aux couleurs du client, cartes
KPI avec variation N vs N-1, slicers, visuels ECharts, navigation à deux
niveaux). Deux livrables complémentaires : **`cadrage.md`** (le cadrage
consolidé) et **`presentation/maquette.html`** (la validation visuelle).

**L'utilisateur fournit TROIS choses** : le **nom du client**, le
**`matrice.xlsx` rempli** (Thèmes › Sujets › Indicateurs + priorités, sources,
fiabilités, formules, axes) déposé dans `clients/<Nom>/matrice.xlsx`, et le
**logo** (`logo.png`) + la **couleur primaire** (hex). Tout le reste est
**télé-guidé par questionnaire** : je propose, l'utilisateur valide ou ajuste.
Les données (`donnees.xlsx`) sont **générées par moi** (`scripts/generate-data.py`,
2 années civiles closes) — jamais fournies par l'utilisateur. Je ne crée
**jamais** le logo.

## Différence avec le dépôt `Prototypage`
`Prototypage` invente le schéma + la navigation depuis un questionnaire métier.
Ici, le **cadrage vient du `matrice.xlsx`** : je m'appuie sur ses colonnes
(**Axes d'analyses** → dimensions, **Formules** → sémantique des mesures,
**Priorités** → périmètre, **Provenance/Source/Fiabilité** → métadonnées et
marqueur `*`). Le périmètre de la maquette est **filtré par priorité**.

## Interdictions de lecture (bloquant — gain de temps critique)

- **Ne JAMAIS lire `references/`** (`TEMPLATE.md`, `template.html`) : ils
  documentent le moteur de rendu pour sa maintenance. Le HTML/CSS/JS n'est
  plus jamais écrit à la main — il sort de `render.py` + `template.html`.
- **Ne JAMAIS lire la maquette d'un autre client** (pas de
  `glob clients/*/presentation`).
- **Ne pas relire `generate-data.py` / `extract-data.py` à chaque run** — la
  section « Patterns réutilisables » + les 2 fichiers d'exemple
  (`clients/_template/data-spec.example.json`, `nav.example.json`) suffisent.
- **Ne JAMAIS relancer le smoke test à la main** : `render.py` l'exécute déjà
  (exit 0 exigé — s'il échoue, `render.py` échoue).

## Flux de démarrage (déclenché par `/cadrage <Nom>`)

1. Le nom vient de l'argument (si absent, je le demande). **Casse respectée
   telle quelle**, je ne propose aucun nom.
2. Je confirme le nom via l'outil `question` (option **Oui** + saisie libre) —
   je ne crée rien tant qu'il n'est pas confirmé.
3. Garde client existant : si `clients/<Nom>/` existe, je demande (régénérer
   la maquette / refaire le cadrage / modifier le nom).
4. Si l'utilisateur est en mode PLAN, je demande le passage en BUILD **une
   seule fois**.
5. Je crée `clients/<Nom>/` avec `CLIENT.md` (copie du template, nom
   pré-rempli) + un `matrice.xlsx` vierge (copie du modèle) si l'utilisateur
   n'en a pas. Aucun logo créé.
6. Je demande les **trois fournitures en UNE seule question** directive dont
   voici le libellé canonique (à recopier, `<Nom>` substitué) :

   > **3 fournitures pour démarrer :**
   >
   > 1. **MATRICE** — déposez le `matrice.xlsx` **rempli avec le client**
   >    (Thèmes › Sujets › Indicateurs, priorités, sources, fiabilités)
   >    **exactement** ici : `clients/<Nom>/matrice.xlsx`
   > 2. **LOGO** — déposez votre logo (PNG, fond transparent) ici :
   >    `clients/<Nom>/logo.png`
   > 3. **COULEUR PRIMAIRE** — ci-dessous, **sélectionnez « Type your own
   >    answer »** puis saisissez **uniquement** le code hex (ex. `#00A1B1`).
   >
   > ⚠️ Ne cochez pas d'option : choisissez « Type your own answer » et
   > collez le code hex.

   Options : **une seule**, échappatoire —
   `{"label": "Pas encore prêt", "description": "Je dépose les fichiers d'abord"}`.
   Le chemin normal est la **saisie libre** (le hex) ; je n'accepte que ça.
   Un clic sur l'échappatoire → j'attends. Je m'arrête pour attendre.
7. Cadrage (Phase 0), livrable cadrage (Phase 1), génération données (Phase 2),
   maquette + pitch (Phase 3).

## Phase 0 — Cadrage (depuis matrice.xlsx)

**Pattern** : je propose un artefact complet (jamais de page blanche),
l'utilisateur valide ou ajuste en texte libre. Les décisions techniques
(formules KPI, types de charts, dispatch dans les pages, schéma en étoile)
sont miennes — l'utilisateur ne les voit jamais.

### Étape 0.1 — Parsing du matrice.xlsx
```bash
python .opencode/skills/cadrage-prototypage/scripts/parse-matrice.py clients/<Nom>/matrice.xlsx
```
Il écrit `clients/<Nom>/cadrage.json` (thèmes › sujets › KPI normalisés +
stats). **Bloquant** si le fichier est vide ou manque la colonne `Indicateurs`.
Je lis ensuite `cadrage.json` pour les étapes suivantes (je ne relis plus
l'Excel).

### Étape 0.2 — Question 1 : Périmètre priorité (validation)
Via l'outil `question`, options cliquables avec **les compteurs calculés**
depuis `cadrage.json` (`stats.scope`) :
- `Hautes uniquement (N KPI)`
- `Hautes + Moyennes (N KPI)`
- `Hautes + Moyennes + Basses (N KPI)`
(+ saisie libre « Sinon « Type your own answer ». »).

Je retiens le `scope` (clé `haute` | `haute_moyenne` | `haute_moyenne_basse`),
qui filtre les KPI entrant dans la maquette. Je le mémorise pour la Phase 1.

### Étape 0.3 — Question 2 : Proposition globale unique
Je présente en une seule proposition compacte, cohérente de bout en bout :
- **Schéma en étoile** dérivé du matrice.xlsx : table de faits (`FAIT_X`),
  **mesures** issues des **Formules** des indicateurs (≤ 3 additives + ≤ 1
  flag 0/1 par taux), **dimensions** issues des **Axes d'analyses**
  (cardinalités ≤ 40), **entité « personne »** si un axe s'y prête
  (`DIM_CLIENT`, `DIM_UTILISATEUR`…).
- **Arbre de navigation** : pages → sous-pages → KPIs. **Thèmes ≠ pages et
  Sujets ≠ sous-pages** : je PROPOSE un regroupement lisible (regrouper des
  thèmes proches, scinder un thème dense), 3-5 KPIs par sous-page, ≤ 4 visuels.
  Chaque KPI hérite de sa **fiabilité** (`reliability`) et de sa **source**
  (`source` = « Système : <provenance> — Source : <source données> ») issues
  du matrice.xlsx — celles `partielle`/`inconnue` porteront un `*`.
- **Couleurs secondaires + titre/sous-titre** : le Primary vient du client ;
  je propose les valeurs canoniques du mode (table ci-dessous), **chaque
  couleur nommée en clair**. Titre/sous-titre déduits du domaine.

→ Une seule validation via l'outil `question` : **Valider** / **Version plus
riche** / **Version plus compacte** (+ saisie libre).

**Couleurs canoniques et cohérence** (mode dérivé de la luminance du Primary) :

| Champ | Mode clair | Mode sombre | Raison UX |
|---|---|---|---|
| Surface / Cards | `#FFFFFF` | `#1E293B` | les cartes « surgissent » du canevas |
| Canvas Background | `#F1F5F9` | `#0F172A` | fond neutre, jamais saturé |
| Card Frame Color | = Surface | = Surface | un seul réglage par défaut |
| Border / Divider | `#CBD5E1` | `#334155` | gris neutre visible mais doux |

Règles : Surface plus claire que le Canvas ; Canvas peu saturé (≤ ~12 %) ;
Border gris désaturé. Le texte sur bandeau (`--on-primary`) est dérivé
automatiquement par `render.py` (WCAG AA).

## Phase 1 — Livrable cadrage (cadrage.md)
```bash
python .opencode/skills/cadrage-prototypage/scripts/generate-cadrage.py <Nom> --scope <scope>
```
Il écrit `clients/<Nom>/cadrage.md` : synthèse (compteurs par priorité/fiabilité),
détail par thème (Sujet / Indicateur / Priorité / Système source / Source
données / Fiabilité / Formule / Commentaires + axes), section « Périmètre
maquette » (KPI retenus selon le scope) et « Alertes fiabilité » (tous les
KPI `partielle`/`inconnue`). C'est le **livrable de cadrage** signé avec le
client.

## Phase 2 — Génération (CLIENT.md + data-spec.json + donnees.xlsx)

1. **J'écris `CLIENT.md`** complet (identité, couleurs validées, « Contexte &
   Données », section « Cadrage & périmètre » avec le scope retenu et le nb
   d'indicateurs marqués) et **`data-spec.json`** (schéma validé + `seed`
   fixe — schéma : `clients/_template/data-spec.example.json`).
2. **Je génère les données** :
   ```bash
   python .opencode/skills/cadrage-prototypage/scripts/generate-data.py clients/<Nom>/data-spec.json
   ```
   Le générateur écrit `donnees.xlsx` conforme **par construction** aux
   contraintes de l'extracteur, sur les **2 années civiles closes**.
3. **Auto-contrôle bloquant** : le générateur relance l'extracteur sur le
   fichier produit et compare au spec — toute divergence est bloquante.

## Phase 3 — Maquette & pitch (nav.json → build-views.py → render.py)

1. **J'écris `nav.json`** : l'arbre validé en Phase 0, en intentions courtes
   (schéma ci-dessous). **Chaque KPI/visuel porte `reliability`/`source`**
   depuis le matrice.xlsx. C'est la **seule** chose que j'écris en Phase 3.
2. **Génération mécanique de `views.json`** :
   ```bash
   python .opencode/skills/cadrage-prototypage/scripts/build-views.py <Nom>
   ```
   Étend `nav.json` en `views.json` complet (dispatch KPI/visuels, donut
   ≤ 6 modalités sinon hbar, humanisation, formats) et **valide chaque
   référence** contre les données. Propage `reliability`/`source` (marqueur `*`).
3. **Génération de la maquette** :
   ```bash
   python .opencode/skills/cadrage-prototypage/scripts/render.py <Nom>
   ```
   Parse `CLIENT.md` (couleurs, `--on-primary` WCAG), injecte DATA + SPEC
   dans le template, écrit `presentation/maquette.html` (avec marqueurs `*` +
   tooltip + légende pied de page) **puis lance le smoke test** (exit 0 exigé).
4. **Boucle de validation avant pitch** — smoke test vert, je pose via
   l'outil `question` : *« La maquette est prête. Passer au pitch de
   présentation ? Sinon « Type your own answer » pour ajuster. »* — option
   cliquable : **Génération de pitch.md**. Ajustement → je modifie `nav.json`
   (ou `data-spec.json` + régénération), je relance `build-views.py` puis
   `render.py`, puis je **repose la même question**.
5. **Pitch du conseiller** :
   ```bash
   python .opencode/skills/cadrage-prototypage/scripts/generate-pitch.py <Nom>
   ```
   Écrit `presentation/pitch.md` : storytelling limité aux KPI/visuels
   percutants (flag `pitch: true`), valeurs réelles année N + variation vs N-1.
6. J'indique l'ouverture : `start clients/<Nom>/presentation/maquette.html`
   (et la lecture de `cadrage.md` + `presentation/pitch.md` avant de présenter).

**Cas « régénérer la maquette » (client existant)** : je réutilise
`CLIENT.md` + `data-spec.json` + `cadrage.json` existants ; si `nav.json`
existe je passe à l'étape 2, sinon je l'écris depuis l'arbre validé.

## Schéma nav.json (complet — rien d'autre n'est supporté)

```json
{
  "labels": {"<clé brute des données>": "<libellé affiché (accents, casse)>"},
  "pages": [
    {"name": "…", "desc": "… (popover info ; {CUR_YEAR}/{PREV_YEAR} substitués)",
     "subs": [
       {"name": "…",
        "kpis": [
          {"type": "count",  "label": "…"},
          {"type": "sum",    "m": "MESURE", "label": "…", "fmt": "eur"},
          {"type": "active", "label": "…"},
          {"type": "ratio",  "num": "MESURE", "den": "_count", "label": "…", "fmt": "pct",
           "reliability": "partielle", "source": "Système : … — Source : …"},
          {"type": "scalar", "from": "NB_MA_DIM", "label": "…", "sub": "…"},
          {"type": "top",    "from": "MaDim", "label": "…"}
        ],
        "visuals": [
          {"type": "line",       "m": "MESURE", "title": "…"},
          {"type": "ratio-line", "num": "MESURE", "den": "_count", "title": "…"},
          {"type": "dim",   "dim": "MaDim", "m": "MESURE", "title": "…"},
          {"type": "cat",   "from": "MA_FEUILLE.MaColonne", "title": "…"},
          {"type": "stacked", "dim": "MaDim", "m": "MESURE", "title": "…"},
          {"type": "table", "dim": "MaDim", "m": "MESURE", "cols": ["AUTRE_MESURE"], "title": "…"}
        ]}
     ]}
  ]
}
```

- **KPI** : `count` · `sum` · `active` (entité personne) · `ratio`
  (`den` : `_count` | `ACTIVE` | mesure | `SCALARS.x`) · `scalar` (statique) ·
  `top` (valeur dominante).
- **Visuels** : `dim`/`cat` → **donut si ≤ 6 modalités, sinon hbar top-10**
  (override `"as": "donut"|"hbar"`). `table` accepte `"cat"` et `"share"`.
- **Défauts automatiques** si absents : `label`/`title` humanisés, `fmt`/`unit`
  inférés du nom de mesure.
- **`"pitch": true`** optionnel = mis en avant dans `pitch.md`.
- **`"reliability"`/`"source"`** optionnels sur tout KPI/visuel :
  `fiable` (défaut, rien) · `partielle` (`*` orange) · `inconnue` (`*` rouge).
  Issus du matrice.xlsx (`Fiabilités des données` + `Provenance/Source`).
  Une `Sources des données` vide → `inconnue` (source non identifiée).
- **Bornes (bloquant)** : 3-5 KPI et ≤ 4 visuels par sous-page (6 KPI max) ;
  toute référence inconnue = erreur listant les identifiants disponibles.
- Exemple complet : `clients/_template/nav.example.json`.

## Mapping matrice.xlsx → maquette

| Colonne matrice.xlsx | Usage dans le skill |
|---|---|
| Thèmes | Structure de cadrage (≠ pages) ; j'en propose un regroupement |
| Sujets | Sous-structure de cadrage (≠ sous-pages) |
| Indicateurs | Libellés des KPI |
| Descriptions | Sous-titres / popover info |
| Priorités | Filtre de périmètre (Question 1) : Haute / Moyenne / Basse |
| Provenance systèmes sources | Tooltip du `*` (l'applicatif d'origine) |
| Sources des données | Tooltip du `*` (table/entrepôt) ; vide → fiabilité `inconnue` |
| Fiabilités des données | Niveau du marqueur : Fiable / Partielle / Inconnue |
| Axes d'analyses | Dimensions du schéma + slicers |
| Formules | Sémantique du KPI (sum / ratio / count / flag) |
| Commentaires | Notes éventuelles dans le cadrage |

## Patterns réutilisables (assemblage, pas invention)

> La STRUCTURE d'une maquette est générique (schéma en étoile + catalogue de
> types KPI/visuels). Seul le CONTENU est spécifique au client — et ici il
> est **ancré sur le matrice.xlsx**. Phase 2 = ASSEMBLER, jamais réinventer.

### Checklist structurelle (toujours vraie)
- 1 faits `FAIT_*`, pk `ID_*`, date_col `DATE`, « 1 ligne = 1 événement daté ».
- Mesures : ≤ 3 additives + au plus 1 flag 0/1 PAR KPI de taux.
- Dimensions : issues des Axes d'analyses ; colonnes ≤ 40 modalités (viser 3-6).
- 1 entité « personne » si un axe s'y prête (regex
  client|utilisateur|employe|…) pour les KPI `active`.
- 1 `extra_sheet` si besoin d'un donut « statut » et/ou de scalars hors-ligne.

### Catalogue de motifs (intention → recette)

| Intention | data-spec | nav.json |
|---|---|---|
| Volume | faits | `{type:"count"}` |
| Total d'une grandeur | mesure additive | `{type:"sum", m, fmt:auto}` |
| Moyenne / panier | mesure | `{type:"ratio", num:M, den:"_count"}` |
| Taux / précision / respect | mesure 0/1 (avg ~p) | `{type:"ratio", num:FLAG, den:"_count", fmt:"pct"}` |
| Coût par unité | 2 mesures (€ + volume) | `{type:"ratio", num:€, den:VOL}` |
| Actifs / entités servies | dim personne | `{type:"active"}` |
| Couverture / cardinalité | dim col | `{type:"scalar", from:"NB_<COL>"}` |
| Valeur dominante | dim col / cat | `{type:"top", from:"<Col>"}` |
| Répartition ≤ 6 | dim/cat | `{type:"dim"|"cat"}` → donut auto |
| Répartition > 6 | dim | `{type:"dim", as:"hbar", top:10}` |
| Détail tabulaire | dim/cat + mesure | `{type:"table"}` |
| Évolution | mesure / flag | `{type:"line", m}` / `{type:"ratio-line"}` |

Formats auto : PCT/TAUX→pct, COUT/PRIX/MONTANT→eur, KM→km, DUREE/DELAI→dur.

## Sources de données

- `matrice.xlsx` — **ENTRÉE** : cadrage rempli avec le client (3 fournitures).
  Modèle vierge : `Matrice.xlsx` (racine) + `clients/_template/matrice.xlsx`.
- `cadrage.json` — matrice.xlsx normalisé (écrit par `parse-matrice.py`).
- `cadrage.md` — **livrable cadrage** (écrit par `generate-cadrage.py`).
- `CLIENT.md` — contrat de marque écrit par le skill ; `render.py` n'y lit que
  l'identité et les couleurs.
- `data-spec.json` — spec de génération (écrit par le skill).
- `donnees.xlsx` — généré par `generate-data.py`. Contrat extrait : `FACTS` /
  `BY_DIM` / `DIM_COUNTS` / `CATEGORY_COUNTS` / `ACTIVE_MASKS` / `SCALARS` /
  `META`, grain mensuel.
- `.data-cache.json` — cache du contrat DATA (invalidé si le xlsx change).
- `nav.json` — arbre de navigation en intentions (écrit par le skill).
- `views.json` — carte visuelle complète (**générée par `build-views.py`**).
- `logo.png` — fourni par l'utilisateur (jamais créé par le skill).
- `presentation/maquette.html` — le rendu (marqueurs `*` + tooltip + légende).
- `presentation/pitch.md` — script du conseiller.
- Modèle de départ : `clients/_template/`.

## Règles (tout le reste est garanti par les scripts et le template)

- **Cadrage depuis matrice.xlsx (bloquant)** : l'utilisateur fournit nom +
  matrice.xlsx rempli + logo + couleur primaire. Je ne réclame jamais un Excel
  de données — les chiffres sont générés (fictifs).
- **Périmètre par priorité (bloquant)** : seuls les KPI du scope retenu
  (Question 1) entrent dans la maquette ; `cadrage.md` couvre l'ensemble.
- **Marqueur de fiabilité (3 niveaux)** : `partielle` → `*` orange,
  `inconnue` → `*` rouge, `fiable` → rien ; tooltip natif + légende pied de
  page ; source de données vide → `inconnue`.
- **Couleurs secondaires nommées en clair (bloquant)** : toute couleur proposée
  est accompagnée de son nom en toutes lettres.
- **Un KPI = une valeur parlante** : je choisis le chiffre unique que le
  libellé signifie (build-views.py fait le reste).
- **Formats `fmt`/`unit`** : `int | km | eur | f1 | dur | pct | text`.
- **Aucune erreur JS tolérée (bloquant)** : le smoke test de `render.py` doit
  passer (exit 0) — s'il échoue, je corrige `nav.json` (jamais le HTML) et je
  relance `build-views.py` + `render.py`.
