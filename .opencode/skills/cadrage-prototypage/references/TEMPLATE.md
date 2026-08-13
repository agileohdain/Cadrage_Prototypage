# TEMPLATE.md — Invariants de la maquette (maintenance de `template.html`)

> ⚠️ **Maintenance du template uniquement.** Ce fichier documente les invariants
> de `references/template.html` pour qui le **modifie**. Il ne doit **jamais être
> lu pendant une génération client** (`/cadrage`) : tout ce dont le skill a
> besoin en run est dans `SKILL.md`, et le HTML/CSS/JS n'est plus jamais écrit à
> la main — il sort de `render.py` + `template.html`.
>
> Format : une règle par ligne + la régression qu'elle prévient. Le code de
> vérité est `template.html` — ne pas recopier le code ici, y renvoyer.

## 1. Canevas & mise en page

- Canevas fixe **1920×1080** (16:9), mis à l'échelle du viewport par
  `transform: scale(...)` avec centrage par translate — jamais de scrollbars,
  jamais de centrage flexbox sur la boîte non-scalée (rogne le canevas à gauche
  si viewport < 1920).
- Échelle d'espacement unique : **grille 8px stricte (8/16/24 px)** — aucun
  gap/padding/margin hors-grille (jamais 6, 10, 12, 14…). La colonne `.content`
  est un flex à **un seul `gap:var(--gap)` (= 16px)** défini dans `:root` ;
  aucun padding-top/bottom ad hoc par bloc (rythme visuel brouillon sinon).
- `.content` commence **sous** le bandeau (`top:calc(97px + var(--gap))`,
  `right`/`bottom:var(--gap)`) — `top:0` ferait chevaucher la navigation par-dessus
  le titre. **Plus de footer** : la mention « données fictives » et la légende de
  fiabilité sont dans l'infobulle d'info (`.pop-note`).
- Conteneurs statiques dédiés `#navL1` / `#navL2` / `#kpis` / `#visuals`,
  chacun réécrit indépendamment — composer par concaténation d'`innerHTML`
  dans un conteneur partagé détruit les nœuds DOM des charts et leurs listeners.
- Rangée KPI à hauteur **fixe 130px** uniforme (footer des cartes aligné).
- Grille visuels `1fr 1fr / 1fr 1fr`, `flex:1; min-height:0` — jamais de
  hauteur fixe en px sur une carte (casse l'égalité des hauteurs).
- `.wide` (`grid-column: 1 / -1`) **uniquement pour 3 visuels** — avec 4 il crée
  une 3ᵉ ligne implicite qui tronque la carte (régression « table tronquée »).
  Avec 4 visuels, la table de détail est l'une des 4 cartes (corps scrollable).
- **Pas de footer** : la mention « Données fictives — Maquette Power BI
  haute-fidélité. » et la légende de fiabilité sont rendues dans l'infobulle
  d'info (`.pop-note`, italique, bordure haute) par `renderInfo()` ; les
  niveaux sont différenciés par **forme + couleur** : `*` orange `#D97706`
  (`partielle`) et `◆` rouge `#DC2626` (`inconnue`).

## 2. Couleurs

- Contrat : `--primary` `--surface` `--canvas` `--card-bg` `--border`
  `--on-primary` `--text-primary` `--text-secondary`, injectées par `render.py`
  depuis `CLIENT.md` (`:root`). **Aucune couleur de marque en dur** dans le
  template — toujours `var(--xxx)`.
- `--on-primary` : dérivé par `render.py` (contraste WCAG AA ≥ 4,5:1 contre
  `--primary`, sinon texte sombre) — un primaire clair (taupe, jaune) rend
  sinon le titre illisible. Tout ce qui est posé sur le bandeau utilise
  `var(--on-primary)` ; jamais `color:var(--surface)` en dur.
- `--text-primary/secondary` : dérivés de la luminance de `--canvas`
  (clair → ardoise foncé ; sombre → clairs).
- Palette catégorielle **toujours dérivée du primaire** (`derivePalette`) —
  jamais d'arc-en-ciel. Exceptions neutres : la série N-1 et « Autres »
  (`C.neutral`), et les badges de variation (vert/rouge/gris sémantiques).

## 3. Bandeau, logo, info

- Bandeau trapézoïdal `var(--primary)` + zone logo trapézoïdale `var(--surface)`
  dessinés en CSS (`clip-path`) — sauf si `bg.svg`/`bg.png` fourni (alors
  l'image prime et rien n'est redessiné).
- Logo centré sur le **centroïde du trapèze** (`padding-right:36px`), pas au
  centre de la boîte 320px (sinon décalé vers le biais) ; `max-height:70px`.
- Titre `<h1>` 26px/700, sous-titre 13px — sobre : pas de 800 ni de classe
  décorative.
- **Une seule** icône info `i`, en haut à droite du bandeau. Popover : page
  active + sous-pages, lignes **cliquables** (`go(page,sub)`), ouverture au
  `:hover` **et** `:focus-within` (clavier/tactile), conteneur de hover commun
  (pas de zone morte entre l'icône et la carte), re-rendu à chaque navigation.

## 4. Pane filtres (gauche)

- Pleine hauteur (`top:calc(97px + var(--gap)); bottom:var(--gap)`), largeur 235px, radius 10px, sans
  bordure ; « Réinitialiser » épinglé en bas (`margin-top:auto`).
- Typographie unique : labels 11px/600/uppercase/`--text-secondary` ;
  contrôles 12px, hauteur 32px, radius 8px (une chiclet et un select alignés).
- **UI seule, jamais liée aux données** : les slicers animent leur état et le
  badge « ● Filtres actifs », mais aucun recompute — KPI et visuels montrent
  toujours l'année N.
- Années en chiclets **ordre chronologique** `[N-1, N]` ; trimestre (≤ 4
  valeurs) en chiclets, mutuellement exclusif avec Mois ; un slicer par
  dimension (chiclets ≤ ~6 valeurs, sinon dropdown).
- La plage de dates alimente le badge (valeurs ≠ fenêtre par défaut = filtre
  actif) ; « Réinitialiser » (icône rotate-ccw, jamais de poubelle — action
  restaurative) réinitialise **aussi** les dates.

## 5. KPI

- **Un KPI = une valeur parlante** — jamais de concaténation (`36 / 9 / 5`).
- Tout KPI temporel affiche sa **variation N vs N-1 sur mois comparables**,
  calculée depuis les agrégats (les ratios recomputent leurs bases, pas le %
  des valeurs arrondies) ; badge masqué si non calculable, jamais inventé.
- `|Δ| < 1 %` → badge **neutre gris** « ≈ stable vs 2024 » — jamais de `+0 %`
  vert ni de `-0,1 %` rouge. Libellés en **années réelles** (`vs 2024`),
  jamais « N-1 ». Même règle pour les sous-titres de visuels.
- KPI statiques (comptages de dimensions) : pas de badge YoY.
- Typographie carte : label 11px/600/uppercase, valeur 28px/700, sub-label
  11px, footer = badge uniquement (`min-height:24px`).

## 6. Visuels (ECharts)

- **Courbes temporelles** : axe Jan→Déc fixe (`01`..`12`), N en `--primary`
  solide 2.5, N-1 en pointillé fin neutre (contexte, pas pair), légende en
  bas, `yAxis.scale:true` (zoom d'amplitude), pas d'`areaStyle` sur N (les
  2 années sont closes — un remplissage partiel ressemble à un bug de rendu).
- **Barres empilées par dimension** : année N seule (jamais N-1 en plus —
  illisible), ≤ 6 séries (top), `scale:false` (les barres partent de 0).
- **Donut** : ≤ ~6 tranches (au-delà → hbar, ou top-N + « Autres » si part de
  total voulue) ; anti-rognage `center:['35%','50%']`, `radius:['48%','66%']`
  + overlay centré sur le même ancrage (un centre plus à gauche rogne les
  labels `%` des tranches de gauche) ; labels `%` toujours visibles au format
  français (`10,5 %`) ; total central **calculé** depuis les tranches, rendu
  en **overlay CSS** (jamais `title`/`graphic` ECharts — centrage non fiable).
- **hbar** : top-10 + « Autres » en neutre, tri décroissant, labels en bout de
  barre (une dimension à 25 modalités écrasées est illisible).
- **Table** : en-tête `--primary`/`--on-primary` sticky, numériques à droite
  en mono, zébrure `--canvas`, corps scrollable.
- **Humanisation** : toute clé brute passe par `LBL()` (map `labels` de
  `views.json`, underscores → espaces, casse) à **chaque** endroit où une clé
  devient du texte affiché (« Depasse » lu comme une coquille sinon).
- Titres de carte 13px/600 à **gauche**, sous-titre 11px à **droite**
  (`space-between`), années réelles résolues (`{CUR_YEAR}`/`{PREV_YEAR}`).

## 7. Données (contrat DATA, grain mensuel)

- `extract-data.py` auto-détecte le modèle (faits = feuille datée la plus
  peuplée avec ≥ 1 mesure ; dims catégorielles ≤ 40 modalités via jointures et
  ponts ; entité « personne » par regex de nom ; feuilles non jointes →
  catégories) et émet `const DATA = {…}` :
  `N`, `MONTH_META`, `FACTS[m][mois]` (+`_count`), `BY_DIM[dim][val][m][mois]`,
  `DIM_COUNTS`, `CATEGORY_COUNTS`, `ACTIVE_MASKS` (bit i = actif au mois i),
  `SCALARS` (`NB_*`, `AVG_*`, `DISTINCT_*`), `META`.
- La maquette embarque les séries mensuelles (pas seulement les agrégats
  finaux) — sinon la variation N vs N-1 est incalculable.
- `data-manifest.json` (optionnel) = override verbatim de l'auto-détection.
- Profil `--profile cyclisme` : contrat de données legacy (compat descendante),
  jamais une référence de layout.
- `.data-cache.json` : cache du contrat (module `scripts/data_cache.py`),
  invalidé par mtime du xlsx/manifeste — régénéré par l'extracteur sinon.

## 8. Moteur JS du template

- Registre de charts en `let charts = {}` (réassigner une `const` = TypeError
  qui blanchit toute la page après la nav) ; dispose + ré-init dans
  `requestAnimationFrame`.
- Init de chart guardé **uniquement** par `if (!el) continue` — un guard sur
  une propriété jamais définie (`el.__chart`) retourne silencieusement à
  chaque appel : page sans exception mais cartes vides.
- Identifiants DATA référencés avec la casse exacte (une typo = ReferenceError
  qui blanchit la sous-page).

## 9. Smoke test (`scripts/smoke-test.js`)

Lancé par `render.py` (exit 0 exigé) — exécute le JS de la maquette dans Node
avec DOM/ECharts simulés : `renderPage()` sans exception, contenu > 2000
caractères, chaque conteneur de chart reçoit son `echarts.init`, **aucun
visuel sans données** (un `from:`/`measure` qui ne résout rien = échec), et
  ce pour **toutes** les sous-pages (`go(p,s)`) et toutes les `VIEWS`.

## 10. Marqueur de fiabilité (`*` / `◆` — cadrage)

- Origine : `reliability` (`fiable` | `partielle` | `inconnue`) + `source` (texte
  libre) sur **tout KPI ou visuel** de `views.json`, propagés depuis `nav.json`
  par `build-views.py` (`_attach_meta`), issus du `Matrice.xlsx`.
- Rendu : `relMark(node)` ajoute un `<span class="rel-mark …">…</span>` après le
  libellé KPI (`kpiCard`) ou le titre de visuel (`buildVisual`). Glyphe + couleur
  (gras) : `*` orange `#D97706` à 16px (`partielle`), `◆` rouge `#DC2626` à 12px
  (`inconnue`, réduit pour équilibrer optiquement avec l'astérisque), `fiable`/absent
  → rien. Dans `kpiCard`, le texte du libellé est
  isolé dans `<span class="kpi-label-txt">` (ellipsis) afin que le marqueur ne
  soit jamais rogné par `overflow:hidden`.
- Tooltip **natif** (`title=""`) : la raison + la `source` + « Détail dans
  cadrage.md ». Pas de tooltip CSS (les cartes sont `overflow:hidden` →
  rognage) ; le `title` est fiable et sans dépendance de positionnement.
- Légende dans l'infobulle (`.pop-note`, plus de footer) : `reliabilityLegend()`
  détecte les niveaux présents et affiche le marqueur correspondant —
  `partielle` → `*` orange `#D97706` « Fiabilité partielle / à valider »,
  `inconnue` → `◆` rouge `#DC2626` « Source non identifiée » — suivie de
  « détail dans cadrage.md ». N'apparaît que si au moins un KPI/visuel est
  marqué.
- Invariant : `relMark` ne lève jamais (node absent → chaîne vide) ; le smoke
  test passe même sans aucun champ `reliability` (rétro-compatible).
