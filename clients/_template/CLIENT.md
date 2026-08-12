# Client : <CLIENT_NAME>

> **Ce fichier est écrit PAR LE SKILL** `cadrage-prototypage`, à partir du
> **`matrice.xlsx`** (rempli avec le client) et de vos réponses au
> **questionnaire guidé** — vous n'avez rien à y saisir. C'est le contrat de
> marque lu par `scripts/render.py` pour générer la maquette. Vous déposez
> **deux** fichiers : `matrice.xlsx` (le cadrage) et `logo.png` (fond
> transparent) ; les données (`donnees.xlsx`) sont **générées par le skill**
> depuis `data-spec.json`. Le livrable de cadrage consolidé est `cadrage.md`.

## Identité

* Brand Name: <CLIENT_NAME>
* Report Title: <Titre du rapport>
* Report Subtitle: <sous-titre / période>

## Couleurs

> Seule la couleur **Primary** est fournie par le client (code hexadécimal,
> ex. `#00A1B1`). Les autres sont **proposées par le skill** — nommées en
> clair (« blanc pur », « gris bleuté très clair »…) — puis validées avec le
> client. Le bandeau est dessiné en CSS avec `Primary` : si un fond `bg.*`
> est déposé (optionnel), sa couleur de bandeau **doit être la même**.

* Primary / Banner Accent: <Primary>   <!-- bandeau, "Filtres", onglets actifs, série primaire -->
* Surface / Cards:        <Surface>    <!-- zone logo, cards -->
* Canvas Background:      <Canvas Background>   <!-- fond du canevas, pane filtres, footer -->
* Card Frame Color:       <Card Frame> <!-- couleur des encadrés (défaut = Surface) -->
* Border / Divider:       <Border>

## Contexte & Données

> Résumé des réponses au questionnaire — le skill le traduit en
> `data-spec.json` puis génère `donnees.xlsx` (2 années civiles closes) via
> `scripts/generate-data.py`.

* Domaine: <ex. pilotage d'une flotte cyclable>
* Faits: <FAIT_X — 1 ligne = 1 événement daté>
* Mesures: <M1 (unité), M2 (unité)>
* Dimensions: <DIM_A (n modalités), DIM_B (n modalités)>
* Entité suivie: <DIM_PERSONNE (n individus)>

## Cadrage & périmètre

> Issu du `matrice.xlsx`. Le périmètre maquette correspond au niveau de priorité
> retenu (Hautes / Hautes+Moyennes / toutes). Les indicateurs à fiabilité
> partielle ou source non identifiée sont marqués d'un `*` sur la maquette —
> détail dans `cadrage.md`.

* Fichier source: matrice.xlsx
* Périmètre maquette: <ex. Hautes + Moyennes (27 indicateurs)>
* Indicateurs marqués (*): <n indicateurs à fiabilité partielle/inconnue>

## Arbre de navigation

> Proposé par le skill et **validé par le client** pendant le questionnaire.
> Chaque sous-page liste ses cartes KPI.

### Page 1: <Titre page 1>

* Sub-page 1.1: <Titre sous-page>
  * KPI 1.1.1: <Libellé KPI>
  * KPI 1.1.2: <Libellé KPI>
* Sub-page 1.2: <Titre sous-page>
  * KPI 1.2.1: <Libellé KPI>

### Page 2: <Titre page 2>

* Sub-page 2.1: <Titre sous-page>
  * KPI 2.1.1: <Libellé KPI>
