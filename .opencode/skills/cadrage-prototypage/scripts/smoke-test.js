#!/usr/bin/env node
/**
 * Smoke test d'une maquette Power BI générée par le skill `cadrage-prototypage`.
 *
 * Exécute le JavaScript inline de la maquette dans Node, avec un DOM et
 * ECharts simulés, puis :
 *   - appelle `renderPage()` (si défini) et vérifie qu'il ne lève pas d'exception ;
 *   - vérifie que la rangée de KPI et la zone de visuels ne sont pas vides ;
 *   - vérifie que chaque rendu appelle bien `echarts.init` (autant de charts
 *     initialisés que de conteneurs rendus) — une maquette peut s'exécuter
 *     sans exception tout en n'affichant AUCUN visuel (guard fautif, ex.
 *     `if (!el || !el.__chart) return;` avec une propriété jamais définie) ;
 *   - parcourt toutes les sous-pages via `go(page, sub)` (si `NAV`/`go` existent) ;
 *   - exécute chaque vue de `VIEWS` avec `aggregates()` (si présents).
 *
 * Usage :  node smoke-test.js <chemin/vers/maquette.html>
 * Sortie : exit code 0 = OK, 1 = au moins un échec, 2 = mauvaise invocation.
 *
 * Pourquoi ce test existe : une seule erreur JS fatale (ReferenceError,
 * réassignation d'une `const`, identifiant mal orthographié) rend la page
 * vide dans le navigateur — la navigation s'affiche mais ni les KPI ni les
 * visuels. Ce test le détecte mécaniquement avant livraison.
 */
const fs = require('fs');

const target = process.argv[2];
if (!target) {
  console.error('usage: node smoke-test.js <chemin/vers/maquette.html>');
  process.exit(2);
}
if (!fs.existsSync(target)) {
  console.error('FAIL: fichier introuvable: ' + target);
  process.exit(1);
}

const html = fs.readFileSync(target, 'utf8');
// Ne capture que les <script> inline (sans attribut src=...).
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(m => m[1])
  .filter(s => s.trim());
if (!scripts.length) {
  console.error('FAIL: aucun <script> inline trouvé dans ' + target);
  process.exit(1);
}
const js = scripts[scripts.length - 1];

/* ---------- DOM / ECharts stubs ---------- */
const dummyParent = {
  querySelector() { return null; },
  appendChild() {},
};
function makeEl(id) {
  return {
    id,
    innerHTML: '',
    className: '',
    value: '0',
    textContent: '',
    style: {},
    dataset: {},
    parentElement: dummyParent,
    children: [],
    appendChild(c) { this.children.push(c); return c; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    addEventListener() {},
    removeEventListener() {},
    setAttribute() {},
    getBoundingClientRect() { return { width: 400, height: 300, left: 0, top: 0 }; },
  };
}
const els = {};
global.__els = els;
global.document = {
  getElementById: (id) => (els[id] = els[id] || makeEl(id)),
  createElement: (tag) => makeEl(tag),
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
  documentElement: { style: { setProperty() {} } },
  body: makeEl('body'),
};
global.window = {
  addEventListener() {},
  removeEventListener() {},
  innerWidth: 1920,
  innerHeight: 1080,
};
global.getComputedStyle = () => ({
  getPropertyValue: () => '#B69E7F',
});
// Compteur d'initialisations ECharts : une maquette dont le rendu
// s'exécute sans exception mais qui n'appelle jamais echarts.init
// affiche des cartes vides dans le navigateur (régression « aucun
// visuel » — ex. guard du type `if (!el || !el.__chart) return;`
// où la propriété testée n'est jamais définie).
global.__chartInits = [];
// Options passées à setOption : permet de détecter les visuels rendus SANS
// données (source `from:` qui ne résout rien — un tel chart passe le test
// d'init mais s'affiche vide au navigateur).
global.__chartOptions = [];
global.echarts = {
  init: (el) => {
    const __id = (el && el.id) || '?';
    global.__chartInits.push(__id);
    return {
      setOption(opt) { global.__chartOptions.push({ id: __id, opt }); },
      dispose() {}, resize() {}, on() {},
    };
  },
};
// Certaines maquettes testent `window.echarts` avant d'initialiser :
// le stub doit l'exposer aussi, sinon l'init est sauté silencieusement
// en test comme en navigateur.
global.window.echarts = global.echarts;
global.requestAnimationFrame = (fn) => fn();

/* ---------- Exécution + vérifications ---------- */
const testHarness = `
;let __failures = 0;
function __check(name, fn) {
  try { fn(); console.log('PASS  ' + name); }
  catch (e) { __failures++; console.log('FAIL  ' + name + '  →  ' + e.message); }
}
// Nombre de conteneurs de chart présents dans le HTML rendu : chaque
// placeholder (<div class="chart"…> / class="chart-echarts"…) doit
// recevoir un echarts.init — sinon la carte reste vide au navigateur.
function __countChartPlaceholders() {
  let n = 0;
  for (const k of Object.keys(__els)) {
    const html = __els[k].innerHTML || '';
    const m = html.match(/class="(?:chart|chart-echarts)"/g);
    if (m) n += m.length;
  }
  return n;
}
// Un visuel « sans données » = aucune série ne contient la moindre valeur
// non nulle (objet {value:…} ou scalaire). Cause classique : un from:/measure
// de views.json qui ne correspond à rien dans DATA — le chart s'initialise
// sans erreur mais s'affiche vide au navigateur.
function __optionHasData(opt) {
  const series = (opt && opt.series) || [];
  for (const s of series) {
    const data = (s && s.data) || [];
    for (const d of data) {
      if (d === null || d === undefined) continue;
      if (typeof d === 'object') { if (d.value !== null && d.value !== undefined) return true; }
      else return true;
    }
  }
  return false;
}
function __checkChartsRendered(contexte) {
  const inits = __chartInits.length;
  if (inits === 0)
    throw new Error('echarts.init jamais appelé (' + contexte + ') — les visuels s\\'afficheront vides. '
      + 'Cause classique : un guard qui retourne toujours (ex. propriété jamais définie sur l\\'élément).');
  const holders = __countChartPlaceholders();
  if (holders > 0 && inits < holders)
    throw new Error(inits + ' chart(s) initialisé(s) pour ' + holders + ' conteneur(s) rendu(s) ('
      + contexte + ') — des visuels resteront vides.');
  const vides = __chartOptions.filter(c => !__optionHasData(c.opt));
  if (vides.length)
    throw new Error(vides.length + ' visuel(s) sans données (' + contexte + ') : '
      + vides.map(c => c.id).join(', ')
      + ' — cause classique : un from:/measure de views.json qui ne résout rien dans DATA.');
}
__check('renderPage() ne lève pas d\\'exception', () => {
  if (typeof renderPage !== 'function') throw new Error('renderPage() non défini');
  __chartInits.length = 0;
  __chartOptions.length = 0;
  renderPage();
  __checkChartsRendered('renderPage initial');
});
__check('contenu principal rendu (KPI + visuels non vides)', () => {
  // Tolérant aux IDs : chaque génération nomme ses conteneurs différemment.
  // Une maquette vide n'écrit que la navigation (quelques centaines de
  // caractères) ; une maquette complète écrit KPI + visuels (> 2000).
  const total = Object.keys(__els).reduce((s, k) => s + ((__els[k].innerHTML) || '').length, 0);
  if (total < 2000) throw new Error('seulement ' + total + ' caractères rendus — la maquette s\\'afficherait sans KPI ni visuels');
});
if (typeof NAV !== 'undefined' && typeof go === 'function') {
  for (let pi = 0; pi < NAV.length; pi++) {
    const subs = NAV[pi].subs || [];
    for (let si = 0; si < subs.length; si++) {
      __check('navigation go(' + pi + ',' + si + ') → ' + (NAV[pi].name || pi), () => {
        __chartInits.length = 0;
        __chartOptions.length = 0;
        go(pi, si);
        __checkChartsRendered('go(' + pi + ',' + si + ')');
      });
    }
  }
}
if (typeof VIEWS !== 'undefined' && typeof aggregates === 'function') {
  const __agg = aggregates();
  for (const k of Object.keys(VIEWS)) {
    __check('VIEWS[' + k + '] s\\'exécute sans exception', () => {
      __chartInits.length = 0;
      __chartOptions.length = 0;
      VIEWS[k](__agg);
      __checkChartsRendered('VIEWS[' + k + ']');
    });
  }
}
if (__failures > 0) {
  console.log('\\nSMOKE TEST FAILED : ' + __failures + ' échec(s). NE PAS LIVRER la maquette en l\\'état.');
  process.exit(1);
}
console.log('\\nSMOKE TEST OK — la maquette peut être livrée.');
process.exit(0);
`;

try {
  eval(js + testHarness);
} catch (e) {
  console.log('FAIL  exécution du script de la maquette  →  ' + e.message);
  console.log('\nSMOKE TEST FAILED : le script ne s\'exécute même pas jusqu\'au bout.');
  process.exit(1);
}
