#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build-views.py — nav.json -> views.json (génération mécanique de la carte visuelle).

Rôle dans le skill cadrage-prototypage
------------------------------------
Le LLM n'écrit plus `views.json` (7-8 Ko, verbeux et risqué pour un petit
modèle) mais un petit `nav.json` (~1 Ko) : l'arbre de navigation validé avec
l'utilisateur, exprimé en **intentions** (pages → sous-pages → KPI/visuels
courts). Ce script l'étend mécaniquement en `views.json` complet, conforme au
schéma attendu par `render.py` / `generate-pitch.py` (cf.
`clients/_template/views.json`), en appliquant les règles qui étaient auparavant
confiées au LLM :

  * mesure -> KPI `sum` YoY + visuel `line` (N vs N-1) ;
  * `ratio` -> KPI ratio YoY + visuel `ratio-line` ;
  * dimension -> visuel `donut` si <= 6 modalités, sinon `hbar` top-10 + « Autres »
    (override possible via "as") ;
  * entité personne -> KPI `active` YoY ;
  * `scalar` / `top` pour les KPI statiques (sans YoY) ;
  * <= 4 visuels par sous-page (bloquant), <= 6 KPI (bloquant) ;
  * libellés auto-humanisés (underscores -> espaces, casse) + map `labels`
    pour les accents ; `fmt`/`unit` inférés du nom de mesure (pct/eur/km/dur/int) ;
  * drapeau `pitch: true` optionnel, repris par `generate-pitch.py`.

Toute référence inconnue (mesure, dimension, scalaire, catégorie) est une
erreur bloquante avec la liste des identifiants disponibles — détectée ici,
avant `render.py` et le smoke test.

Usage :
    python build-views.py <client>                 # clients/<c>/nav.json -> clients/<c>/views.json
    python build-views.py <client> -o <fichier>    # sortie ailleurs (test)

Schéma nav.json : voir clients/_template/nav.example.json.
"""
import sys
import os
import re
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_cache

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MEASURE_AGGS = ("count", "sum", "ratio")


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------
def humanize(k, labels):
    """Miroir Python de humanize() du template (labels d'abord, puis casse)."""
    if k is None:
        return ""
    s = str(k)
    if s in labels:
        return labels[s]
    s = s.replace("_", " ")
    if re.search(r"[A-Z]", s) and re.match(r"^[A-Z0-9 \-]+$", s) and " " in s:
        s = re.sub(r"(?i)\b[a-zà-ÿ]", lambda m: m.group(0).upper(), s.lower())
    return s


def infer_fmt(m):
    """fmt par défaut d'après le nom de mesure (conventions du skill)."""
    u = (m or "").upper()
    if re.search(r"PCT|TAUX|RATE|_TX", u):
        return "pct"
    if re.search(r"COUT|PRIX|MONTANT|VALEUR|EUR", u) or re.search(r"(^|_)CA($|_)", u):
        return "eur"
    if "KM" in u:
        return "km"
    if re.search(r"DUREE|DELAI|MIN", u):
        return "dur"
    return "int"


# ---------------------------------------------------------------------------
# Constructeur avec validation contre le contrat DATA
# ---------------------------------------------------------------------------
class Builder:
    def __init__(self, nav, data):
        self.nav = nav
        self.data = data
        self.labels = nav.get("labels") or {}
        meta = data.get("META") or {}
        self.measures = meta.get("measures") or []
        self.dims = [d["name"] for d in (meta.get("dims") or [])]
        self.activity = meta.get("activity_entity")
        self.scalars = data.get("SCALARS") or {}
        self.by_dim = data.get("BY_DIM") or {}
        self.dim_counts = data.get("DIM_COUNTS") or {}
        self.cat_counts = data.get("CATEGORY_COUNTS") or {}
        self.errors = []

    # -- validation ---------------------------------------------------------
    def err(self, where, msg):
        self.errors.append("%s : %s" % (where, msg))

    def check_measure(self, where, m):
        if m not in self.measures:
            self.err(where, "mesure '%s' inconnue (disponibles : %s)"
                     % (m, ", ".join(self.measures) or "aucune"))
            return False
        return True

    def check_dim(self, where, d):
        if d not in self.dims:
            self.err(where, "dimension '%s' inconnue (disponibles : %s)"
                     % (d, ", ".join(self.dims) or "aucune"))
            return False
        return True

    def check_den(self, where, den):
        ok = (den in ("_count", "ACTIVE") or den in self.measures
              or (den.startswith("SCALARS.") and den.split(".", 1)[1] in self.scalars))
        if not ok:
            self.err(where, "dénominateur '%s' invalide (_count | ACTIVE | mesure | "
                     "SCALARS.x existant)" % den)
        return ok

    def check_scalar(self, where, key):
        bare = key.split(".", 1)[1] if key.startswith("SCALARS.") else key
        if bare not in self.scalars:
            close = [k for k in self.scalars if bare.upper() in k]
            hint = (" — proches : %s" % ", ".join(close[:6])) if close else ""
            self.err(where, "scalaire '%s' inconnu (ex. : %s%s)"
                     % (key, ", ".join(list(self.scalars)[:6]), hint))
            return False
        return True

    def resolve_flat_from(self, where, f):
        """'Prestataire' -> 'DIM_COUNTS.Prestataire' ; chemins complets validés."""
        if "." not in f:
            if not self.check_dim(where, f):
                return None
            return "DIM_COUNTS." + f
        p = f.split(".")
        if p[0] == "DIM_COUNTS" and len(p) == 2:
            if not self.check_dim(where, p[1]):
                return None
        elif p[0] == "CATEGORY_COUNTS" and len(p) == 3:
            if not self.check_cat(where, f):
                return None
        else:
            self.err(where, "from '%s' invalide (DIM_COUNTS.<dim> | "
                     "CATEGORY_COUNTS.<feuille>.<colonne> | nom de dim)" % f)
            return None
        return f

    def check_cat(self, where, f):
        p = f.split(".")
        ok = (len(p) == 3 and p[0] == "CATEGORY_COUNTS"
              and p[1] in self.cat_counts and p[2] in self.cat_counts.get(p[1], {}))
        if not ok:
            avail = ["%s.%s" % (s, c) for s, cols in self.cat_counts.items() for c in cols]
            self.err(where, "catégorie '%s' inconnue (disponibles : %s)"
                     % (f, ", ".join(avail) or "aucune"))
        return ok

    # -- KPI -----------------------------------------------------------------
    def kpi(self, k, where):
        t = k.get("type")
        pitch = {"pitch": True} if k.get("pitch") else {}
        if t == "count":
            return {"label": k.get("label") or "Volume", "agg": "sum",
                    "measure": "_count", "yoy": True, "fmt": "int",
                    "sub": k.get("sub") or "en {CUR_YEAR}", **pitch}
        if t == "sum":
            m = k.get("m")
            if not m:
                return self.err(where, "KPI sum sans 'm' (mesure)"), None
            if not self.check_measure(where, m):
                return None
            return {"label": k.get("label") or humanize(m, self.labels),
                    "agg": "sum", "measure": m, "yoy": True,
                    "fmt": k.get("fmt") or infer_fmt(m),
                    "sub": k.get("sub") or "en {CUR_YEAR}", **pitch}
        if t == "active":
            if not self.activity:
                self.err(where, "KPI 'active' sans entité personne dans le modèle "
                         "(renommez la feuille : client|utilisateur|employe…)")
                return None
            return {"label": k.get("label") or "Actifs", "agg": "active",
                    "yoy": True, "fmt": "int",
                    "sub": k.get("sub") or "actifs en {CUR_YEAR}", **pitch}
        if t == "ratio":
            num, den = k.get("num"), k.get("den") or "_count"
            if not num:
                return self.err(where, "KPI ratio sans 'num'"), None
            ok = self.check_measure(where, num) if num not in ("_count", "ACTIVE") else True
            ok = self.check_den(where, den) and ok
            if not ok:
                return None
            return {"label": k.get("label") or humanize(num, self.labels),
                    "agg": "ratio", "num": num, "den": den, "yoy": True,
                    "fmt": k.get("fmt") or infer_fmt(num),
                    "sub": k.get("sub") or "· {CUR_YEAR}", **pitch}
        if t == "scalar":
            f = k.get("from")
            if not f:
                return self.err(where, "KPI scalar sans 'from'"), None
            key = f if f.startswith("SCALARS.") else "SCALARS." + f
            if not self.check_scalar(where, key):
                return None
            return {"label": k.get("label") or humanize(key.split(".", 1)[1], self.labels),
                    "agg": "scalar", "from": key, "fmt": k.get("fmt") or "int",
                    "sub": k.get("sub") or "", **pitch}
        if t == "top":
            f = k.get("from")
            if not f:
                return self.err(where, "KPI top sans 'from'"), None
            src = self.resolve_flat_from(where, f)
            if not src:
                return None
            return {"label": k.get("label") or humanize(f.split(".")[-1], self.labels),
                    "agg": "top", "from": src, "fmt": "text",
                    "sub": k.get("sub") or "en tête", **pitch}
        self.err(where, "type de KPI inconnu : '%s' (count|sum|active|ratio|scalar|top)" % t)
        return None

    # -- visuels -------------------------------------------------------------
    def dim_card(self, dim):
        return len(self.by_dim.get(dim) or self.dim_counts.get(dim) or {})

    def dim_visual(self, v, where):
        dim = v.get("dim")
        if not dim:
            return self.err(where, "visuel dim sans 'dim'"), None
        if not self.check_dim(where, dim):
            return None
        m = v.get("m") or "_count"
        if m != "_count" and not self.check_measure(where, m):
            return None
        as_ = v.get("as") or ("donut" if self.dim_card(dim) <= 6 else "hbar")
        unit = v.get("unit") or ("int" if m == "_count" else infer_fmt(m))
        title = v.get("title") or (
            "Répartition par " + humanize(dim, self.labels) if m == "_count"
            else humanize(m, self.labels) + " par " + humanize(dim, self.labels))
        pitch = {"pitch": True} if v.get("pitch") else {}
        src = "BY_DIM.%s.%s" % (dim, m)
        if as_ == "donut":
            return {"type": "donut", "from": src, "top": v.get("top") or 6,
                    "title": title, "unit": unit,
                    "centerSub": v.get("centerSub") or
                        (humanize(m, self.labels).lower() if m != "_count" else "total"),
                    "sub": v.get("sub") or "année {CUR_YEAR}", **pitch}
        if as_ == "hbar":
            return {"type": "hbar", "from": src, "top": v.get("top") or 10,
                    "title": title, "unit": unit,
                    "sub": v.get("sub") or "année {CUR_YEAR}", **pitch}
        self.err(where, "as: '%s' invalide (donut|hbar)" % as_)
        return None

    def cat_visual(self, v, where):
        f = v.get("from")
        if not f:
            return self.err(where, "visuel cat sans 'from' (CATEGORY_COUNTS.<feuille>.<col>)"), None
        src = f if f.startswith("CATEGORY_COUNTS.") else "CATEGORY_COUNTS." + f
        if not self.check_cat(where, src):
            return None
        col = src.split(".")[2]
        card = len(self.cat_counts[src.split(".")[1]][col])
        as_ = v.get("as") or ("donut" if card <= 6 else "hbar")
        title = v.get("title") or humanize(col, self.labels)
        pitch = {"pitch": True} if v.get("pitch") else {}
        unit = v.get("unit") or "int"
        if as_ == "donut":
            return {"type": "donut", "from": src, "top": v.get("top") or 6,
                    "title": title, "unit": unit,
                    "centerSub": v.get("centerSub") or humanize(col, self.labels).lower(),
                    "sub": v.get("sub") or "instantané", **pitch}
        return {"type": "hbar", "from": src, "top": v.get("top") or 10,
                "title": title, "unit": unit,
                "sub": v.get("sub") or "instantané", **pitch}

    def table_visual(self, v, where):
        dim, cat = v.get("dim"), v.get("cat")
        if not dim and not cat:
            return self.err(where, "visuel table sans 'dim' ni 'cat'"), None
        if dim and not self.check_dim(where, dim):
            return None
        m = v.get("m") or "_count"
        if m != "_count" and not self.check_measure(where, m):
            return None
        row_label = humanize(dim, self.labels) if dim else None
        if cat:
            src = cat if str(cat).startswith("CATEGORY_COUNTS.") else "CATEGORY_COUNTS." + str(cat)
            if not self.check_cat(where, src):
                return None
            row_label = humanize(src.split(".")[2], self.labels)
            from_ = src
        else:
            from_ = "BY_DIM.%s.%s" % (dim, m)
        cols = [{"label": row_label, "source": "name"}]
        # colonne « self » (valeur propre de la source) toujours présente
        self_lbl = v.get("self_label") or (
            humanize(m, self.labels) if (m != "_count" and not cat) else "Volume")
        cols.append({"label": self_lbl, "source": "self", "num": True,
                     "fmt": "int" if (m == "_count" or cat) else infer_fmt(m)})
        for mm in v.get("cols") or []:
            if not self.check_measure(where, mm):
                return None
            cols.append({"label": humanize(mm, self.labels), "source": "measure:" + mm,
                         "num": True, "fmt": infer_fmt(mm)})
        if v.get("share"):
            den = v["share"]
            den = den if den.startswith("SCALARS.") else "SCALARS." + den
            if not self.check_scalar(where, den):
                return None
            cols.append({"label": v.get("share_label") or "Part",
                         "ratio": {"num": "self", "den": den, "pct": True},
                         "num": True, "fmt": "pct"})
        sort_by = v.get("sortBy") or "self"
        if sort_by != "self" and not sort_by.startswith("measure:"):
            sort_by = "measure:" + sort_by
        title = v.get("title") or (
            "Détail par " + row_label if dim else "Détail — " + row_label)
        out = {"type": "table", "from": from_, "title": title, "sortBy": sort_by,
               "sub": v.get("sub") or ("année {CUR_YEAR}" if dim else "instantané"),
               "cols": cols}
        if v.get("pitch"):
            out["pitch"] = True
        return out

    def visual(self, v, where):
        t = v.get("type")
        pitch = {"pitch": True} if v.get("pitch") else {}
        if t == "line":
            m = v.get("m")
            if not m:
                return self.err(where, "visuel line sans 'm' (mesure)"), None
            if not self.check_measure(where, m):
                return None
            return {"type": "line", "measure": m,
                    "title": v.get("title") or humanize(m, self.labels) + " par mois",
                    "unit": v.get("unit") or infer_fmt(m), **pitch}
        if t == "ratio-line":
            num, den = v.get("num"), v.get("den") or "_count"
            if not num:
                return self.err(where, "visuel ratio-line sans 'num'"), None
            ok = self.check_measure(where, num) if num not in ("_count", "ACTIVE") else True
            ok = self.check_den(where, den) and ok
            if not ok:
                return None
            return {"type": "ratio-line", "num": num, "den": den,
                    "title": v.get("title") or humanize(num, self.labels) + " par mois",
                    "unit": v.get("unit") or infer_fmt(num), **pitch}
        if t == "dim":
            return self.dim_visual(v, where)
        if t == "cat":
            return self.cat_visual(v, where)
        if t == "stacked":
            dim, m = v.get("dim"), v.get("m")
            if not dim or not m:
                return self.err(where, "visuel stacked sans 'dim'/'m'"), None
            if not (self.check_dim(where, dim) and self.check_measure(where, m)):
                return None
            return {"type": "stacked-bars", "from": "BY_DIM.%s.%s" % (dim, m),
                    "title": v.get("title") or
                        humanize(m, self.labels) + " mensuel par " + humanize(dim, self.labels),
                    "unit": v.get("unit") or infer_fmt(m), **pitch}
        if t == "table":
            return self.table_visual(v, where)
        self.err(where, "type de visuel inconnu : '%s' "
                 "(line|ratio-line|dim|cat|stacked|table)" % t)
        return None

    def _attach_meta(self, out, node):
        """Propage reliability/source du noeud nav.json vers views.json.
        Sert au rendu du marqueur * (fiabilité) sur les KPI/visuels."""
        if not isinstance(out, dict):
            return out
        if node.get("reliability"):
            out["reliability"] = node["reliability"]
        if node.get("source"):
            out["source"] = node["source"]
        return out

    # -- arbre ----------------------------------------------------------------
    def build(self):
        pages = []
        for pi, p in enumerate(self.nav.get("pages") or []):
            pw = "page %d '%s'" % (pi + 1, p.get("name", "?"))
            subs = []
            for si, s in enumerate(p.get("subs") or []):
                sw = "%s / sous-page %d '%s'" % (pw, si + 1, s.get("name", "?"))
                kpis = []
                for i, k in enumerate(s.get("kpis") or []):
                    o = self.kpi(k, "%s / KPI %d" % (sw, i + 1))
                    if o:
                        kpis.append(self._attach_meta(o, k))
                visuals = []
                for i, v in enumerate(s.get("visuals") or []):
                    o = self.visual(v, "%s / visuel %d" % (sw, i + 1))
                    if o:
                        visuals.append(self._attach_meta(o, v))
                if len(kpis) > 6:
                    self.err(sw, "%d KPI (> 6 — la rangée devient illisible)" % len(kpis))
                if not kpis:
                    self.err(sw, "aucun KPI valide")
                if len(visuals) > 4:
                    self.err(sw, "%d visuels (> 4 — la grille 2×2 déborde)" % len(visuals))
                if not visuals:
                    self.err(sw, "aucun visuel valide")
                subs.append({"name": s.get("name") or "Sous-page %d" % (si + 1),
                             "kpis": kpis, "visuals": visuals})
            if not subs:
                self.err(pw, "page sans sous-page")
            pages.append({"name": p.get("name") or "Page %d" % (pi + 1),
                          "desc": p.get("desc") or "", "subs": subs})
        if not pages:
            self.err("nav.json", "aucune page")
        if self.errors:
            return None
        return {"labels": self.labels, "pages": pages}


# ---------------------------------------------------------------------------
def main():
    import argparse
    ap = argparse.ArgumentParser(description="nav.json -> views.json (carte visuelle mécanique)")
    ap.add_argument("client", help="nom du dossier client (clients/<client>/nav.json)")
    ap.add_argument("-o", "--out", help="fichier de sortie (défaut: clients/<client>/views.json)")
    args = ap.parse_args()

    cdir = os.path.join(ROOT, "clients", args.client)
    nav_path = os.path.join(cdir, "nav.json")
    xlsx = os.path.join(cdir, "donnees.xlsx")
    for p, lbl in [(cdir, "dossier client"), (nav_path, "nav.json"), (xlsx, "donnees.xlsx")]:
        if not os.path.exists(p):
            raise SystemExit("ERREUR: %s introuvable (%s)." % (lbl, p))

    nav = json.load(open(nav_path, encoding="utf-8"))
    data = data_cache.get_data(xlsx, os.path.join(cdir, "data-manifest.json"))

    b = Builder(nav, data)
    views = b.build()
    if views is None:
        sys.stderr.write("--- build-views : ERREURS ---\n")
        for e in b.errors:
            sys.stderr.write("  * %s\n" % e)
        sys.exit(1)

    out = args.out or os.path.join(cdir, "views.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(views, f, ensure_ascii=False, indent=2)
        f.write("\n")
    n_kpi = sum(len(s["kpis"]) for p in views["pages"] for s in p["subs"])
    n_vis = sum(len(s["visuals"]) for p in views["pages"] for s in p["subs"])
    sys.stderr.write("OK: %s généré (%d pages, %d sous-pages, %d KPI, %d visuels).\n"
                     % (out, len(views["pages"]),
                        sum(len(p["subs"]) for p in views["pages"]), n_kpi, n_vis))


if __name__ == "__main__":
    main()
