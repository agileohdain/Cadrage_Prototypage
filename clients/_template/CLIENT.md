# Client : <CLIENT_NAME>

> **Ce fichier est écrit PAR LE SKILL** `cadrage-prototypage`. C'est le
> **contrat de marque** lu par `render.py` (titre, sous-titre, couleurs) et
> `generate-pitch.py` (titre, sous-titre, domaine) — vous n'avez rien à y
> saisir. Tout vient du **`matrice.xlsx`** et de vos réponses au
> questionnaire. Vous déposez **deux** fichiers : `matrice.xlsx` (le cadrage)
> et `logo.png` (fond transparent) ; les données (`donnees.xlsx`) sont
> **générées par le skill** depuis `data-spec.json`. Le livrable de cadrage
> consolidé est `cadrage.md`.

## Identité

* Brand Name: <CLIENT_NAME>
* Report Title: <Titre du rapport>
* Report Subtitle: <sous-titre / période>
* Domaine: <ex. pilotage d'une flotte cyclable>

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