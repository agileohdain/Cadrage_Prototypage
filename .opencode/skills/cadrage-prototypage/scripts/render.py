#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère clients/<client>/presentation/maquette.html depuis :
  * references/template.html  (scaffold + moteur générique)
  * clients/<client>/CLIENT.md (couleurs, titre, sous-titre)
  * clients/<client>/views.json (pages / sous-pages / KPI / visuels)
  * clients/<client>/donnees.xlsx  (via extract-data.py -> DATA normalisé)

Usage :
  python render.py <client>
  python render.py MonClient

Étapes : parse CLIENT.md -> variables CSS (dont --on-primary WCAG),
extraction DATA normalisée, injection DATA/SPEC/CSS/titre dans le template,
écriture de presentation/maquette.html, puis smoke test (exit 0 exigé).
"""
import sys
import os
import re
import json
import subprocess
import html as htmllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_cache

# Console Windows (cp1252) : force utf-8 pour afficher les accents/flèches.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SKILL = os.path.join(ROOT, ".opencode", "skills", "cadrage-prototypage")
TEMPLATE = os.path.join(SKILL, "references", "template.html")
SMOKE = os.path.join(SKILL, "scripts", "smoke-test.js")


# ----------------------------- CLIENT.md ----------------------------------
def parse_client_md(path):
    txt = open(path, encoding="utf-8").read()
    def field(label):
        m = re.search(r"^\*\s*" + re.escape(label) + r"\s*:\s*(.+?)\s*$", txt, re.M)
        return m.group(1).strip() if m else ""
    title = field("Report Title")
    sub = field("Report Subtitle")
    primary = field("Primary / Banner Accent")
    surface = field("Surface / Cards")
    canvas = field("Canvas Background")
    card = field("Card Frame Color") or surface or "#FFFFFF"
    border = field("Border / Divider")
    if not primary:
        raise SystemExit("ERREUR: 'Primary / Banner Accent' manquant dans CLIENT.md")
    return {
        "title": title, "subtitle": sub,
        "primary": norm_hex(primary), "surface": norm_hex(surface) or "#FFFFFF",
        "canvas": norm_hex(canvas) or "#F1F5F9", "card": norm_hex(card) or "#FFFFFF",
        "border": norm_hex(border) or "#CBD5E1",
    }


def norm_hex(s):
    if not s:
        return ""
    m = re.search(r"(#[0-9A-Fa-f]{6})", s)
    return m.group(1).lower() if m else ""


# ----------------------------- couleurs -----------------------------------
def rel_lum(hexcol):
    h = hexcol.lstrip("#")
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]

    def f(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    R, G, B = f(r), f(g), f(b)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B


def contrast(a, b):
    la, lb = rel_lum(a), rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def text_tokens(canvas_hex):
    """--text-primary/secondary dérivés de la luminance du canvas."""
    return ("#0F172A", "#64748B") if rel_lum(canvas_hex) >= 0.5 else ("#F1F5F9", "#94A3B8")


def css_vars(c):
    on_primary = c["surface"] if contrast(c["surface"], c["primary"]) >= 4.5 else "#0F172A"
    t1, t2 = text_tokens(c["canvas"])
    return (
        ":root{\n"
        "  --primary:%s;\n  --surface:%s;\n  --canvas:%s;\n  --card-bg:%s;\n  --border:%s;\n"
        "  --text-primary:%s;\n  --text-secondary:%s;\n  --on-primary:%s;\n}\n"
    ) % (c["primary"], c["surface"], c["canvas"], c["card"], c["border"], t1, t2, on_primary)


# ----------------------------- extraction ---------------------------------
def extract_data(xlsx, manifest=None):
    """Littéral JS du contrat DATA — via le cache partagé (.data-cache.json)."""
    return data_cache.literal(data_cache.get_data(xlsx, manifest))


# ----------------------------- rendu --------------------------------------
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
    spec = json.load(open(views_json, encoding="utf-8"))
    spec["css"] = {"primary": cfg["primary"], "surface": cfg["surface"],
                   "canvas": cfg["canvas"], "border": cfg["border"], "card": cfg["card"]}

    data_lit = extract_data(xlsx, os.path.join(cdir, "data-manifest.json"))
    tpl = open(TEMPLATE, encoding="utf-8").read()

    title = cfg["title"] or (cfg.get("brand") or client)
    repl = {
        "__CSS_VARS__": css_vars(cfg),
        "__BRAND_TITLE__": htmllib.escape(title),
        "__BRAND_SUB__": htmllib.escape(cfg["subtitle"]),
        "__DATA__": data_lit,
        "__SPEC__": json.dumps(spec, ensure_ascii=False),
    }
    out = tpl
    for k, v in repl.items():
        out = out.replace(k, v)

    prs = os.path.join(cdir, "presentation")
    os.makedirs(prs, exist_ok=True)
    idx = os.path.join(prs, "maquette.html")
    open(idx, "w", encoding="utf-8").write(out)
    sys.stderr.write("OK: %s généré.\n" % idx)

    # smoke test
    r = subprocess.run(["node", SMOKE, idx], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    sys.stdout.write(r.stdout or "")
    sys.stderr.write(r.stderr or "")
    if r.returncode != 0:
        raise SystemExit("SMOKE TEST FAILED (exit %d)." % r.returncode)
    sys.stderr.write("Maquette livrée.\n")


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: python render.py <client>\n")
        sys.exit(2)
    render(sys.argv[1])


if __name__ == "__main__":
    main()
