#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de données fictives : data-spec.json -> donnees.xlsx

Rôle dans le skill cadrage-prototypage
------------------------------------
L'utilisateur ne fournit PAS les données : le skill les GÉNÈRE à partir d'un
spec (`clients/<client>/data-spec.json`) validé avec l'utilisateur pendant le
questionnaire guidé. Ce script écrit un classeur Excel qui respecte **par
construction** les contraintes de `extract-data.py` :

  * dates **typées** (datetime) — jamais du texte ;
  * PK = 1re colonne, nommée ID_*, unique ;
  * clés étrangères nommées EXACTEMENT comme la PK de la feuille cible ;
  * dimensions catégorielles <= 40 modalités (CAT_MAX de l'extracteur) ;
  * entité « personne » nommée pour matcher PERSON_RE (DIM_CLIENT,
    DIM_UTILISATEUR, DIM_EMPLOYE…).

Période générée : les **2 années civiles closes** précédant l'année courante
(dynamique : en 2026 -> 2024+2025 ; en 2027 -> 2025+2026). L'année N est donc
toujours complète et la variation vs N-1 comparable sur 12 mois.

Modèle du spec (voir clients/_template/data-spec.example.json) :

  fact        : {name, pk, date_col, rows_per_month:[min,max]}
  measures    : [{name, avg, std, min, decimals, trend_pct, seasonality[12]}
                 ou {name, per:{measure, ratio_avg, ratio_std}, min, decimals}]
  dimensions  : [{sheet, pk, size, columns:[{name, values|{label:poids},
                  parent?, values:{parent:{label:poids}}}]}]
  bridges     : [{name, pk, left:<feuille dim>, right:<feuille dim>, size}]
                -> la faits référence le pont (FK = pk du pont) au lieu de
                   référencer directement les deux dimensions.
  extra_sheets: [{name, pk, size, columns:[{name, type:categorical|numeric|id,
                  ...}]}]  (feuilles NON jointes -> CATEGORY_COUNTS / SCALARS)

Usage :
  python generate-data.py clients/<client>/data-spec.json
  python generate-data.py <spec.json> -o <donnees.xlsx>

Après écriture, le script relance extract-data.py en **auto-contrôle** et
affiche le modèle détecté (faits / mesures / dimensions / entité active) ;
toute divergence avec le spec est signalée sur stderr.

Dépendance : openpyxl (pip install openpyxl)
"""
import sys
import os
import json
import random
import argparse
import datetime

try:
    import openpyxl
except ImportError:
    sys.stderr.write("ERREUR: openpyxl manquant -> pip install openpyxl\n")
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import data_cache
CAT_MAX = 40  # aligné sur extract-data.py

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------
def weighted_choice(rng, values):
    """values = {label: poids} ou [label, ...] (poids égaux)."""
    if isinstance(values, dict):
        labels, weights = list(values.keys()), list(values.values())
    else:
        labels, weights = list(values), [1.0] * len(values)
    return rng.choices(labels, weights=weights, k=1)[0]


def closed_period():
    """2 années civiles closes : (année-2, année-1). Retourne [(y, m), ...]."""
    today = datetime.date.today()
    y0, y1 = today.year - 2, today.year - 1
    return [(y, m) for y in (y0, y1) for m in range(1, 13)]


def check_spec(spec):
    """Validations bloquantes ou avertissements, avant toute génération."""
    fact = spec.get("fact") or {}
    for k in ("name", "pk", "date_col"):
        if not fact.get(k):
            raise SystemExit("ERREUR spec: fact.%s manquant." % k)
    dims = spec.get("dimensions") or []
    seen_sheets = {fact["name"]}
    for d in dims:
        sh = d.get("sheet")
        if not sh or not d.get("pk") or not d.get("size"):
            raise SystemExit("ERREUR spec: dimension incomplète (sheet/pk/size).")
        if sh in seen_sheets:
            raise SystemExit("ERREUR spec: feuille dupliquée '%s'." % sh)
        seen_sheets.add(sh)
        cols = d.get("columns") or []
        names = set()
        for c in cols:
            vals = c.get("values")
            if c.get("parent"):
                if c["parent"] not in names:
                    raise SystemExit("ERREUR spec: colonne '%s' dépend de '%s' "
                                     "qui doit être déclarée AVANT dans %s."
                                     % (c["name"], c["parent"], sh))
                parent = next(p for p in cols if p["name"] == c["parent"])
                pvals = set(parent["values"].keys()) if isinstance(parent["values"], dict) else set(parent["values"])
                missing = pvals - set(vals.keys())
                if missing:
                    raise SystemExit("ERREUR spec: %s.%s ne couvre pas les "
                                     "valeurs parentes %s." % (sh, c["name"], sorted(missing)))
                n = sum(len(v) for v in vals.values())
            else:
                n = len(vals)
            if n > CAT_MAX:
                sys.stderr.write("ATTENTION spec: %s.%s a %d modalités (> %d) — "
                                 "l'extracteur l'ignorerait.\n" % (sh, c["name"], n, CAT_MAX))
            names.add(c["name"])
    for b in spec.get("bridges") or []:
        for k in ("name", "pk", "left", "right", "size"):
            if not b.get(k):
                raise SystemExit("ERREUR spec: bridge incomplet (%s)." % k)
        for side in ("left", "right"):
            if b[side] not in [d["sheet"] for d in dims]:
                raise SystemExit("ERREUR spec: bridge '%s' référence une "
                                 "dimension inconnue '%s'." % (b["name"], b[side]))
        seen_sheets.add(b["name"])
    for e in spec.get("extra_sheets") or []:
        if not e.get("name") or not e.get("pk") or not e.get("size"):
            raise SystemExit("ERREUR spec: extra_sheet incomplète (name/pk/size).")
        seen_sheets.add(e["name"])
    if not spec.get("measures"):
        raise SystemExit("ERREUR spec: au moins une mesure requise.")
    names = [m["name"] for m in spec["measures"]]
    for m in spec["measures"]:
        per = m.get("per")
        if per and per.get("measure") not in names[:names.index(m["name"])]:
            raise SystemExit("ERREUR spec: mesure '%s' liée à '%s' qui doit "
                             "être déclarée AVANT." % (m["name"], (per or {}).get("measure")))


# ---------------------------------------------------------------------------
# Génération
# ---------------------------------------------------------------------------
def gen_dimension(rng, d):
    rows = []
    for i in range(1, d["size"] + 1):
        row = {d["pk"]: i}
        for c in d.get("columns") or []:
            if c.get("parent"):
                pv = row[c["parent"]]
                row[c["name"]] = weighted_choice(rng, c["values"][pv])
            else:
                row[c["name"]] = weighted_choice(rng, c["values"])
        rows.append(row)
    return rows


def gen_bridge(rng, b, dims_by_sheet):
    left = dims_by_sheet[b["left"]]
    right = dims_by_sheet[b["right"]]
    rows = []
    for i in range(1, b["size"] + 1):
        rows.append({
            b["pk"]: i,
            left["pk"]: rng.randint(1, left["size"]),
            right["pk"]: rng.randint(1, right["size"]),
        })
    return rows


def gen_extra_sheet(rng, e):
    rows = []
    for i in range(1, e["size"] + 1):
        row = {e["pk"]: i}
        for c in e.get("columns") or []:
            t = c.get("type", "categorical")
            if t == "categorical":
                row[c["name"]] = weighted_choice(rng, c["values"])
            elif t == "numeric":
                v = rng.gauss(c.get("avg", 100), c.get("std", 20))
                v = max(c.get("min", 0), v)
                row[c["name"]] = round(v, c.get("decimals", 0))
            elif t == "id":
                row[c["name"]] = rng.randint(1, c.get("pool", e["size"]))
        rows.append(row)
    return rows


def gen_facts(rng, spec, months, dims_by_sheet, bridges_by_name):
    fact = spec["fact"]
    measures = spec["measures"]
    bridged = set()
    for b in spec.get("bridges") or []:
        bridged.add(b["left"])
        bridged.add(b["right"])
    direct_dims = [d for d in spec.get("dimensions") or [] if d["sheet"] not in bridged]

    rows = []
    pk = 1
    n0 = len(months)
    for idx, (y, m) in enumerate(months):
        lo, hi = fact.get("rows_per_month", [30, 60])
        n_rows = rng.randint(lo, hi)
        for _ in range(n_rows):
            day = rng.randint(1, 28)  # safe pour tous les mois
            row = {fact["pk"]: pk, fact["date_col"]: datetime.datetime(y, m, day)}
            for d in direct_dims:
                row[d["pk"]] = rng.randint(1, d["size"])
            for b in spec.get("bridges") or []:
                row[b["pk"]] = rng.randint(1, b["size"])
            values = {}
            for meas in measures:
                per = meas.get("per")
                if per:
                    base = values[per["measure"]]
                    v = base * rng.gauss(per.get("ratio_avg", 1), per.get("ratio_std", 0.2))
                else:
                    season = meas.get("seasonality") or [1.0] * 12
                    trend = meas.get("trend_pct", 0)
                    factor = season[m - 1] * ((1 + trend / 100) ** (idx / 12.0))
                    v = rng.gauss(meas.get("avg", 100) * factor, meas.get("std", 20))
                v = max(meas.get("min", 0), v)
                v = round(v, meas.get("decimals", 0))
                values[meas["name"]] = v
                row[meas["name"]] = v
            rows.append(row)
            pk += 1
    return rows


def write_workbook(path, sheets):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets:
        ws = wb.create_sheet(title=name[:31])  # limite Excel
        if not rows:
            continue
        header = list(rows[0].keys())
        ws.append(header)
        for r in rows:
            ws.append([r.get(h) for h in header])
    wb.save(path)


# ---------------------------------------------------------------------------
# Auto-contrôle via extract-data.py
# ---------------------------------------------------------------------------
def self_check(xlsx_path, spec):
    # data_cache écrit aussi .data-cache.json à côté du xlsx : render.py et
    # generate-pitch.py réutiliseront ce contrat sans re-parser le classeur.
    data = data_cache.get_data(xlsx_path)
    meta = data["META"]
    problems = []
    if meta["fact_sheet"] != spec["fact"]["name"]:
        problems.append("faits détectées '%s' != spec '%s'"
                        % (meta["fact_sheet"], spec["fact"]["name"]))
    sm = set(meta["measures"])
    want = {m["name"] for m in spec["measures"]}
    if sm != want:
        problems.append("mesures détectées %s != spec %s" % (sorted(sm), sorted(want)))
    bridged = set()
    for b in spec.get("bridges") or []:
        bridged.add(b["left"])
        bridged.add(b["right"])
    want_dims = set()
    for d in spec.get("dimensions") or []:
        for c in d.get("columns") or []:
            want_dims.add(c["name"])
    got_dims = {d["name"] for d in meta["dims"]}
    if got_dims != want_dims:
        problems.append("dimensions détectées %s != spec %s"
                        % (sorted(got_dims), sorted(want_dims)))
    if not meta.get("activity_entity"):
        problems.append("entité active NON détectée — renommez la feuille "
                        "personne (utilisateur|user|employe|client|person|"
                        "agent|membre|collab).")
    if data["N"] != 24:
        problems.append("période détectée = %d mois (24 attendus)." % data["N"])
    if problems:
        sys.stderr.write("--- AUTO-CONTROLE : DIVERGENCES ---\n")
        for p in problems:
            sys.stderr.write("  * %s\n" % p)
        sys.exit(1)
    sys.stderr.write("AUTO-CONTROLE OK: faits='%s' | %d mois | mesures=%s | "
                     "dims=%s | entité_active=%s\n"
                     % (meta["fact_sheet"], data["N"], meta["measures"],
                        [d["name"] for d in meta["dims"]], meta["activity_entity"]))
    sys.stderr.write("--- CLÉS DISPONIBLES POUR nav.json ---\n")
    sys.stderr.write("  Mesures        : %s\n"
                     % ", ".join(list(meta["measures"]) + ["_count"]))
    sys.stderr.write("  Dimensions     : %s\n"
                     % ", ".join(d["name"] for d in meta["dims"]))
    scalars = sorted(data.get("SCALARS", {}).keys())
    if scalars:
        sys.stderr.write("  SCALARS        : %s\n" % ", ".join(scalars))
    cats = sorted("%s.%s" % (s, c)
                  for s, cols in data.get("CATEGORY_COUNTS", {}).items()
                  for c in cols)
    if cats:
        sys.stderr.write("  CATEGORY_COUNTS: %s\n" % ", ".join(cats))
    if meta.get("activity_entity"):
        sys.stderr.write("  Entité active  : %s\n" % meta["activity_entity"])


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Générateur data-spec.json -> donnees.xlsx")
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", help="chemin de sortie (défaut: donnees.xlsx "
                                        "à côté du spec)")
    args = ap.parse_args()

    if not os.path.exists(args.spec):
        sys.stderr.write("ERREUR: spec introuvable: %s\n" % args.spec)
        sys.exit(2)
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    check_spec(spec)

    rng = random.Random(spec.get("seed", 42))
    months = closed_period()
    dims_by_sheet = {}
    sheets = []
    for d in spec.get("dimensions") or []:
        rows = gen_dimension(rng, d)
        dims_by_sheet[d["sheet"]] = {**d, "_rows": rows}
        sheets.append((d["sheet"], rows))
    bridges_by_name = {}
    for b in spec.get("bridges") or []:
        rows = gen_bridge(rng, b, dims_by_sheet)
        bridges_by_name[b["name"]] = rows
        sheets.append((b["name"], rows))
    facts = gen_facts(rng, spec, months, dims_by_sheet, bridges_by_name)
    # la faits en tête de classeur (convention, non requis par l'extracteur)
    sheets.insert(0, (spec["fact"]["name"], facts))
    for e in spec.get("extra_sheets") or []:
        sheets.append((e["name"], gen_extra_sheet(rng, e)))

    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.spec)),
                                   "donnees.xlsx")
    write_workbook(out, sheets)
    sys.stderr.write("OK: %s écrit (%d lignes de faits, %d feuilles, %d mois "
                     "%d-%d).\n" % (out, len(facts), len(sheets), len(months),
                                    months[0][0], months[-1][0]))
    self_check(out, spec)


if __name__ == "__main__":
    main()
