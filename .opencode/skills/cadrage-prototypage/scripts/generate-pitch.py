#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère clients/<client>/presentation/pitch.md — le « script du conseiller ».

Rôle dans le skill cadrage-prototypage
------------------------------------
À la fin de la Phase 3, une fois la maquette validée (`presentation/maquette.html`),
le skill déclenche une boucle de validation ; quand l'utilisateur choisit
« Génération de pitch.md », ce script produit un **pitch de présentation
narrative** pour le conseiller qui présentera la maquette à un client.

Le pitch est généré depuis :
  * `CLIENT.md`   (titre, sous-titre, domaine métier)
  * `views.json`  (pages → sous-pages → KPI / visuels, + drapeaux `pitch: true`)
  * `donnees.xlsx` (via `extract-data.py` -> contrat DATA) : valeurs **réelles**
    année N + variation N vs N-1, injectées dans le script.

Sélection éditoriale : le pitch ne reprend PAS tout l'arbre — seulement les KPI /
visuels les plus percutants (flag `pitch: true` dans `views.json`, à défaut une
heuristique : 2 KPI à plus forte |variation| + 1 visuel par sous-page « développée »).

Usage :
  python generate-pitch.py <client>
  python generate-pitch.py veloh
"""
import sys
import os
import re
import json

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SKILL = os.path.join(ROOT, ".opencode", "skills", "cadrage-prototypage")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_cache


# ---------------------------------------------------------------------------
# Extraction & agrégats (miroir de template.html : aggregates/kpiValue/kpiYoy)
# ---------------------------------------------------------------------------
def extract_data(xlsx):
    """Contrat DATA parsé — via le cache partagé (.data-cache.json). Le
    manifeste éventuel (data-manifest.json à côté du xlsx) est honoré,
    comme dans render.py."""
    manifest = os.path.join(os.path.dirname(os.path.abspath(xlsx)), "data-manifest.json")
    return data_cache.get_data(xlsx, manifest)


def aggregates(DATA, cur, prev):
    months = DATA["MONTH_META"]
    measures = DATA["META"].get("measures") or []
    facts = DATA["FACTS"]
    nset = {mm["month"] for mm in months if mm["year"] == cur}
    agg = {"c__count": 0.0, "p__count": 0.0}
    for mn in measures:
        agg["c_" + mn] = 0.0
        agg["p_" + mn] = 0.0
    for i, mm in enumerate(months):
        if mm["year"] == cur:
            for mn in measures:
                agg["c_" + mn] += facts[mn][i]
            agg["c__count"] += facts["_count"][i]
        elif mm["year"] == prev and mm["month"] in nset:
            for mn in measures:
                agg["p_" + mn] += facts[mn][i]
            agg["p__count"] += facts["_count"][i]
    masks = DATA.get("ACTIVE_MASKS") or {}
    cmask = pmask = 0
    for i, mm in enumerate(months):
        if mm["year"] == cur:
            cmask |= (1 << i)
        if mm["year"] == prev and mm["month"] in nset:
            pmask |= (1 << i)
    agg["cActifs"] = sum(1 for k in masks if masks[k] & cmask)
    agg["pActifs"] = sum(1 for k in masks if masks[k] & pmask)
    return agg


def resolve_scalar(DATA, from_):
    if not from_:
        return None
    p = from_.split(".")
    if p[0] == "SCALARS":
        return DATA["SCALARS"].get(p[1])
    return None


def resolve_flat(DATA, from_, cur):
    if not from_:
        return {}
    p = from_.split(".")
    if p[0] == "DIM_COUNTS":
        return DATA["DIM_COUNTS"].get(p[1], {})
    if p[0] == "CATEGORY_COUNTS":
        return DATA["CATEGORY_COUNTS"].get(p[1], {}).get(p[2], {})
    if p[0] == "BY_DIM":
        src = DATA["BY_DIM"].get(p[1], {})
        meas = p[2]
        out = {}
        for v, slot in src.items():
            if slot and meas in slot:
                out[v] = sum(slot[meas][i] for i, mm in enumerate(DATA["MONTH_META"])
                             if mm["year"] == cur)
        return out
    return {}


def resolve_num(DATA, agg, tok, cur):
    if tok == "ACTIVE":
        return agg["cActifs"] if cur else agg["pActifs"]
    if tok == "_count":
        return agg["c__count"] if cur else agg["p__count"]
    c = ("c_" if cur else "p_") + tok
    if c in agg and agg[c] is not None:
        return agg[c]
    if tok and tok.startswith("SCALARS."):
        return resolve_scalar(DATA, tok)
    return None


def top_named(flat):
    if not flat:
        return ""
    top = max(flat.values())
    return " · ".join(k for k, v in flat.items() if v == top)


def kpi_value(DATA, k, agg, cur):
    a = k["agg"]
    if a == "sum":
        m = k.get("measure") or "_count"
        return agg["c__count"] if m == "_count" else agg.get("c_" + m)
    if a == "active":
        return agg["cActifs"]
    if a == "scalar":
        return resolve_scalar(DATA, k.get("from"))
    if a == "top":
        return top_named(resolve_flat(DATA, k.get("from"), cur))
    if a == "ratio":
        n = resolve_num(DATA, agg, k.get("num"), True)
        d = resolve_num(DATA, agg, k.get("den"), True)
        return n / d if d else None
    return None


def kpi_yoy(DATA, k, agg):
    if not k.get("yoy"):
        return None
    a = k["agg"]
    if a == "sum":
        m = k.get("measure") or "_count"
        c = agg["c__count"] if m == "_count" else agg.get("c_" + m)
        p = agg["p__count"] if m == "_count" else agg.get("p_" + m)
        return _pct(c, p)
    if a == "active":
        return _pct(agg["cActifs"], agg["pActifs"])
    if a == "ratio":
        cn = resolve_num(DATA, agg, k.get("num"), True)
        cp = resolve_num(DATA, agg, k.get("num"), False)
        dn = resolve_num(DATA, agg, k.get("den"), True)
        dp = resolve_num(DATA, agg, k.get("den"), False)
        if dn and dp:
            return _pct(cn / dn, cp / dp)
    return None


def _pct(c, p):
    return (c - p) / p * 100 if p else None


# ---------------------------------------------------------------------------
# Formatage (fr-FR : groupements espaces, virgule décimale)
# ---------------------------------------------------------------------------
def fr_int(v):
    return format(int(round(v)), ",d").replace(",", " ")


def fr_1(v):
    s = format(v, ",.1f").replace(",", " ").replace(".", ",")
    return s


def fmt_val(v, fmt):
    if v is None:
        return "—"
    if fmt == "km":
        if v >= 1000:
            return format(v / 1000, ",.1f").replace(",", " ").replace(".", ",") + " k"
        return fr_int(v)
    if fmt == "eur":
        if v >= 1000:
            return format(v / 1000, ",.1f").replace(",", " ").replace(".", ",") + " k €"
        return fr_int(v) + " €"
    if fmt == "f1":
        return fr_1(v)
    if fmt == "dur":
        mn = int(round(v))
        return (str(mn // 60) + " h " + str(mn % 60)) if mn >= 60 else str(mn) + " min"
    if fmt == "pct":
        return fr_1(v) + " %"
    if fmt == "text":
        return str(v)
    return fr_int(v)


def fmt_yoy(v, prev_year):
    if v is None:
        return ""
    y = str(prev_year)
    if abs(v) < 1:
        return "≈ stable vs " + y
    sign = "+" if v >= 0 else "−"
    return sign + fr_1(abs(v)) + " % vs " + y


# ---------------------------------------------------------------------------
# Sélection éditoriale
# ---------------------------------------------------------------------------
def pick_kpis(DATA, kpis, agg, n, cur_year):
    """n KPI : drapeaux `pitch:true` d'abord, puis plus forte |voY|, puis premiers."""
    if not kpis:
        return []
    flagged = [k for k in kpis if k.get("pitch")]
    ranked = sorted([k for k in kpis if k.get("yoy")],
                    key=lambda k: abs(kpi_yoy(DATA, k, agg) or 0), reverse=True)
    prefer = flagged if len(flagged) >= n else (flagged + ranked + kpis)
    chosen = []
    seen = set()
    for k in prefer:
        ki = id(k)
        if ki in seen:
            continue
        seen.add(ki)
        chosen.append(k)
        if len(chosen) >= n:
            break
    if len(chosen) < n:
        for k in kpis:
            if id(k) in seen:
                continue
            seen.add(id(k))
            chosen.append(k)
            if len(chosen) >= n:
                break
    return chosen


def pick_visual(DATA, visuals, agg, cur_year):
    if not visuals:
        return None
    for v in visuals:
        if v.get("pitch"):
            return v
    for v in visuals:
        if v.get("type") != "table":
            return v
    return visuals[0]


def is_developed(sub):
    if sub.get("kpis") and any(k.get("pitch") for k in sub["kpis"]):
        return True
    if sub.get("visuals") and any(v.get("pitch") for v in sub["visuals"]):
        return True
    return False


# ---------------------------------------------------------------------------
# Rédaction narrative
# ---------------------------------------------------------------------------
VISUAL_LABEL = {"line": "courbe", "ratio-line": "courbe de ratio",
                "donut": "donut", "parts-donut": "donut de décomposition",
                "hbar": "barres horizontales", "stacked-bars": "barres empilées",
                "table": "tableau de détail"}


def kpi_insight(DATA, k, cur_year):
    a = k["agg"]
    m = k.get("measure") or ""
    if a == "sum" and m == "_count":
        return "volume cumulé sur l'année %d." % cur_year
    if a == "sum" and k.get("fmt") == "eur":
        return "montant cumulé sur l'année %d." % cur_year
    if a == "sum":
        return "cumul sur l'année %d." % cur_year
    if a == "ratio":
        return "ratio moyen calculé sur l'année %d (indicateur de performance)." % cur_year
    if a == "active":
        return "entités actives au moins un mois de l'année %d." % cur_year
    if a == "top":
        return "valeur qui domine le classement (ex-æquo possibles)."
    return "valeur statique du modèle de données (sans variation)."


def visual_insight(DATA, v, cur_year):
    t = v.get("type")
    if t in ("line", "ratio-line"):
        return ("Évolution mensuelle (axe Jan→Déc, %d vs %d) — regardez la pente "
                "de l'année %d par rapport à %d." % (cur_year, cur_year - 1,
                                                     cur_year, cur_year - 1))
    flat = resolve_flat(DATA, v.get("from"), cur_year)
    top = top_named(flat)
    if t == "donut":
        return ("Répartition en part de marché interne ; la tranche dominante est "
                "« %s »." % (top or "—"))
    if t == "hbar":
        return ("Classement (top-10 + « Autres ») ; le leader est « %s »."
                % (top or "—"))
    if t == "stacked-bars":
        dim = (v.get("from") or "").split(".")[1] if v.get("from") else ""
        return ("Volume mensuel par %s, année %d — repérez la saisonnalité et le "
                "mix." % (dim or "dimension", cur_year))
    if t == "parts-donut":
        return ("Décomposition avec poste résiduel « Autres » ; le poste principal "
                "est « %s »." % (top or "—"))
    if t == "table":
        return ("Table de détail triée ; le leader est « %s »." % (top or "—"))
    return "Visuel à commenter selon les chiffres affichés."


def message_cle(k1, k2, y1, y2, prev_year):
    labels = (k1["label"] if k1 else "") + ((" et " + k2["label"]) if k2 else "")
    if not y1 and not y2:
        return "%s — la vue de référence de cette page." % (labels or "Les indicateurs")
    if y1 and y1 > 1 and (y2 is None or y2 > 1):
        return "Ces indicateurs progressent sur l'année : %s." % labels
    if y1 and y1 < -1 and (y2 is None or y2 < -1):
        return "Point d'attention : %s affichent un repli." % labels
    return "Des signaux contrastés sur %s : à nuancer dans la présentation." % labels


def transition(next_ref):
    return "_Transition : « Passons au point suivant. » → %s_" % next_ref


# ---------------------------------------------------------------------------
# Rendu pitch.md
# ---------------------------------------------------------------------------
def parse_client_md(path):
    txt = open(path, encoding="utf-8").read()
    def field(label):
        m = re.search(r"^\*\s*" + re.escape(label) + r"\s*:\s*(.+?)\s*$", txt, re.M)
        return m.group(1).strip() if m else ""
    return {"brand": field("Brand Name"), "title": field("Report Title"),
            "subtitle": field("Report Subtitle"), "domaine": field("Domaine")}


def render(client):
    cdir = os.path.join(ROOT, "clients", client)
    if not os.path.isdir(cdir):
        raise SystemExit("ERREUR: dossier client introuvable: clients/" + client)
    client_md = os.path.join(cdir, "CLIENT.md")
    views_json = os.path.join(cdir, "views.json")
    xlsx = os.path.join(cdir, "donnees.xlsx")
    for p, lbl in [(client_md, "CLIENT.md"), (views_json, "views.json"), (xlsx, "donnees.xlsx")]:
        if not os.path.exists(p):
            raise SystemExit("ERREUR: %s manquant dans clients/%s" % (lbl, client))

    cfg = parse_client_md(client_md)
    views = json.load(open(views_json, encoding="utf-8"))
    DATA = extract_data(xlsx)

    cur = max(mm["year"] for mm in DATA["MONTH_META"])
    prev = cur - 1
    agg = aggregates(DATA, cur, prev)
    pages = views.get("pages") or []

    if not pages:
        raise SystemExit("ERREUR: views.json sans page.")

    # ------ structuration ------
    durations = {"open": 2, "close": 1, "dev": 4, "brief": 2}
    total = durations["open"] + durations["close"]
    dev_subs = {}
    for pi, pg in enumerate(pages):
        subs = pg.get("subs") or []
        for si, sub in enumerate(subs):
            dev = (si == 0) or is_developed(sub)
            dev_subs[(pi, si)] = dev
            total += durations["dev"] if dev else durations["brief"]

    # ------ ouverture ------
    first_kpis = (pages[0].get("subs") or [{}])[0].get("kpis") or []
    hl = pick_kpis(DATA, first_kpis, agg, 2, cur)
    headline = []
    for k in hl:
        v = kpi_value(DATA, k, agg, True)
        y = kpi_yoy(DATA, k, agg)
        headline.append("%s (%s)" % (fmt_val(v, k.get("fmt") or "int"), fmt_yoy(y, prev))
                        if y else fmt_val(v, k.get("fmt") or "int"))

    periode = "%s–%s" % (prev, cur)
    domain = re.sub(r"[,;\s]+$", "", (cfg["domaine"] or "").strip()) or "la performance du client"

    lines = []
    lines.append("# Pitch de présentation — %s" % (cfg["brand"] or client))
    lines.append("> %s · Maquette %s vs %s" % (cfg["title"] or cfg["brand"], cur, prev))
    lines.append("> Durée totale indicative : ≈ %d min" % int(total))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Ouverture (≈ %d min)" % durations["open"])
    lines.append("")
    lines.append("« Bonjour, merci de nous accueillir. Je vous propose de découvrir "
                 "notre maquette d'un tableau de bord qui pilote %s, sur les deux "
                 "exercices clos %s." % (domain, periode))
    if headline:
        htxt = ", ".join(headline)
        lines.append("Le chiffre à retenir pour ouvrir la discussion : **%s**." % htxt)
    lines.append("»")
    lines.append("")
    p1 = "Page 2 : " + (pages[0]["name"] if pages[0].get("name") else "Synthèse")
    lines.append("*Transition : « Commençons par la vue d'ensemble. » → %s.*" % p1)
    lines.append("")
    lines.append("---")
    lines.append("")

    # ------ pages ------
    for pi, pg in enumerate(pages):
        pn = pi + 2
        lines.append("## %d. %s" % (pn, pg.get("name", "Page %d" % pn)))
        lines.append("")
        subs = pg.get("subs") or []
        # liste des références suivantes pour les transitions
        for si, sub in enumerate(subs):
            sname = sub.get("name", "Sous-page %d" % (si + 1))
            ref = "%d.%d %s" % (pn, si + 1, sname)
            dev = dev_subs[(pi, si)]
            d = durations["dev"] if dev else durations["brief"]
            lines.append("### %s (≈ %d min)" % (ref, d))
            lines.append("")
            lines.append("**Objectif** : %s" % (pg.get("desc") or
                          "Présenter la sous-page %s." % sname))
            kpis = pick_kpis(DATA, sub.get("kpis") or [], agg, 2 if dev else 1, cur)
            if kpis:
                lines.append("**À citer** :")
                lines.append("")
                for k in kpis:
                    v = kpi_value(DATA, k, agg, True)
                    y = kpi_yoy(DATA, k, agg)
                    val = fmt_val(v, k.get("fmt") or "int")
                    ytxt = fmt_yoy(y, prev)
                    if y:
                        lines.append("- **%s — %s** *(%s)* : %s" %
                                     (k.get("label"), val, ytxt,
                                      kpi_insight(DATA, k, cur)))
                    else:
                        lines.append("- **%s — %s** : %s" %
                                     (k.get("label"), val,
                                      kpi_insight(DATA, k, cur)))
                lines.append("")
            if dev and len(kpis) >= 2:
                y1 = kpi_yoy(DATA, kpis[0], agg)
                y2 = kpi_yoy(DATA, kpis[1], agg)
                lines.append("**Message clé** : « %s »" % message_cle(kpis[0], kpis[1], y1, y2, prev))
                lines.append("")
            v = pick_visual(DATA, sub.get("visuals") or [], agg, cur)
            if dev and v:
                vl = VISUAL_LABEL.get(v.get("type"), "visuel")
                lines.append("**Visuel appuyant** — %s (%s) :" % (v.get("title"), vl))
                lines.append("")
                lines.append("« %s »" % visual_insight(DATA, v, cur))
                lines.append("")
            # transition
            nxt = None
            if si + 1 < len(subs):
                nxt = "%d.%d %s" % (pn, si + 2, subs[si + 1].get("name", ""))
            elif pi + 1 < len(pages):
                nxt = "Page %d : %s" % (pn + 1, pages[pi + 1].get("name", ""))
            else:
                nxt = "la Clôture"
            lines.append(transition(nxt))
            lines.append("")
        lines.append("---")
        lines.append("")

    # ------ clôture ------
    lines.append("## %d. Clôture (≈ %d min)" % (len(pages) + 2, durations["close"]))
    lines.append("")
    lines.append("« Ce que nous avons vu : la maquette donne sur une même lecture "
                 "%s et les indicateurs utiles pour décider. Je vous propose "
                 "d'identifier ensemble les KPI à suivre en réel, et nous "
                 "retravaillerons la maquette dans cette direction. »" % domain)
    lines.append("")
    lines.append("---")
    lines.append("*Données fictives générées pour la maquette — Pitch conseiller (à ajuster).*")
    lines.append("")

    out = "\n".join(lines)
    prs = os.path.join(cdir, "presentation")
    os.makedirs(prs, exist_ok=True)
    dst = os.path.join(prs, "pitch.md")
    open(dst, "w", encoding="utf-8").write(out)
    sys.stderr.write("OK: %s généré (%d lignes, durée ≈ %d min).\n"
                     % (dst, len(lines), int(total)))


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: python generate-pitch.py <client>\n")
        sys.exit(2)
    render(sys.argv[1])


if __name__ == "__main__":
    main()
