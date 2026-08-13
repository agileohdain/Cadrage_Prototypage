#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate-cadrage.py — consolide le cadrage (cadrage.json) en un document
markdown lisible : cadrage.md. C'est le livrable de la phase de cadrage,
complémentaire de la maquette HTML.

Produit :
  * En-tête (client, date, fichier source, périmètre maquette retenu).
  * Synthèse (compteurs par priorité et par fiabilité).
  * Un tableau détaillé par thème (Sujet / Indicateur / Priorité / Système
    source / Source données / Fiabilité / Formule / Commentaires).
  * Une section « Périmètre maquette » (KPI retenus selon le scope priorité).
  * Une section « Alertes fiabilité » (indicateurs partiels / source inconnue).

Usage :
  python generate-cadrage.py <client> [--scope haute|haute_moyenne|haute_moyenne_basse]
  Défaut : --scope haute_moyenne_basse
"""
import os
import re
import sys
import json
import datetime

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

SCOPES = {
    "haute": ("Hautes uniquement", ("Haute",)),
    "haute_moyenne": ("Hautes + Moyennes", ("Haute", "Moyenne")),
    "haute_moyenne_basse": ("Hautes + Moyennes + Basses", ("Haute", "Moyenne", "Basse")),
}

FIAB_LABEL = {
    "fiable": ("Fiable", "OK"),
    "partielle": ("Partielle", "ATTENTION"),
    "inconnue": ("Inconnue", "RISQUE"),
}


def client_name(cdir, client):
    md = os.path.join(cdir, "CLIENT.md")
    if os.path.exists(md):
        txt = open(md, encoding="utf-8").read()
        m = re.search(r"^\*\s*Brand Name\s*:\s*(.+?)\s*$", txt, re.M)
        if m and m.group(1).strip() and not m.group(1).strip().startswith("<"):
            return m.group(1).strip()
    return client


def md_escape(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def scope_kpis(themes, kept):
    out = []
    for t in themes:
        for s in t["sujets"]:
            for k in s["kpis"]:
                if (k.get("priorite") or "") in kept or not k.get("priorite"):
                    # KPI sans priorité explicitement assignée -> inclus si scope large
                    if (k.get("priorite") or "") in kept:
                        out.append((t["theme"], s["sujet"], k))
    return out


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: python generate-cadrage.py <client> "
                         "[--scope haute|haute_moyenne|haute_moyenne_basse]\n")
        sys.exit(2)
    client = sys.argv[1]
    scope_key = "haute_moyenne_basse"
    if "--scope" in sys.argv:
        i = sys.argv.index("--scope")
        scope_key = sys.argv[i + 1]
    if scope_key not in SCOPES:
        raise SystemExit("ERREUR: scope inconnu '%s' (haute | haute_moyenne | "
                         "haute_moyenne_basse)" % scope_key)

    cdir = os.path.join(ROOT, "clients", client)
    cjson = os.path.join(cdir, "cadrage.json")
    if not os.path.exists(cjson):
        raise SystemExit("ERREUR: cadrage.json introuvable: %s\n"
                         "Lancez d'abord parse-matrice.py." % cjson)
    cadrage = json.load(open(cjson, encoding="utf-8"))
    themes = cadrage.get("themes") or []
    stats = cadrage.get("stats") or {}

    scope_label, kept = SCOPES[scope_key]
    name = client_name(cdir, client)
    date = datetime.date.today().strftime("%d/%m/%Y")

    lines = []
    A = lines.append
    A("# Cadrage — %s" % name)
    A("")
    A("> Livrable de la phase de cadrage, consolidé depuis `%s` (rempli avec le "
      "client). Complémentaire de la maquette HTML : il documente **l'ensemble** "
      "des indicateurs (y compris hors maquette), leurs priorités, sources et "
      "fiabilités." % cadrage.get("source", "matrice.xlsx"))
    A("")
    A("- **Date** : %s" % date)
    A("- **Périmètre maquette retenu** : %s" % scope_label)
    A("- **Indicateurs cadrés** : %d" % stats.get("total", 0))
    A("")

    # Synthèse
    A("## Synthèse")
    A("")
    A("**Par priorité**")
    A("")
    A("| Priorité | Indicateurs | Dans la maquette ? |")
    A("|---|---:|:---:|")
    in_scope = scope_key
    cumul = 0
    for p in ("Haute", "Moyenne", "Basse"):
        n = stats.get(p, 0)
        yes = "Oui" if p in kept else "—"
        A("| %s | %d | %s |" % (p, n, yes))
    if stats.get("sans_prio"):
        A("| (sans priorité) | %d | — |" % stats.get("sans_prio", 0))
    A("")
    A("**Par fiabilité**")
    A("")
    A("| Fiabilité | Indicateurs | Marqueur maquette |")
    A("|---|---:|:---:|")
    for f in ("fiable", "partielle", "inconnue"):
        lab, _ = FIAB_LABEL[f]
        mark = "—" if f == "fiable" else ("`*` orange" if f == "partielle" else "`◆` rouge")
        A("| %s | %d | %s |" % (lab, stats.get(f, 0), mark))
    A("")

    # Détail par thème
    A("## Détail par thème")
    A("")
    A("> Les **Thèmes** et **Sujets** structurent le cadrage métier — ils ne "
      "correspondent pas nécessairement aux pages/sous-pages de la maquette "
      "(regroupées pour la lisibilité).")
    A("")
    for t in themes:
        A("### %s" % t["theme"])
        A("")
        A("| Sujet | Indicateur | Priorité | Système source | Source données | "
          "Fiabilité | Formule | Commentaires |")
        A("|---|---|---|---|---|---|---|---|")
        for s in t["sujets"]:
            for k in s["kpis"]:
                flab, _ = FIAB_LABEL.get(k.get("fiabilite", "inconnue"), ("?", "?"))
                A("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    md_escape(s["sujet"]), md_escape(k["indicateur"]),
                    k.get("priorite") or "—",
                    md_escape(k.get("systeme_source", "")) or "—",
                    md_escape(k.get("source_donnees", "")) or "—",
                    flab, md_escape(k.get("formule", "")) or "—",
                    md_escape(k.get("commentaires", "")) or "—"))
        A("")
        for s in t["sujets"]:
            for k in s["kpis"]:
                if k.get("axes"):
                    A("- **%s** — axes d'analyse : %s"
                      % (k["indicateur"], ", ".join(k["axes"])))
        A("")

    # Périmètre maquette
    scoped = []
    for t in themes:
        for s in t["sujets"]:
            for k in s["kpis"]:
                if (k.get("priorite") or "") in kept:
                    scoped.append((t["theme"], s["sujet"], k))
    A("## Périmètre maquette (%s)" % scope_label)
    A("")
    if scoped:
        A("%d indicateurs retenus pour la maquette." % len(scoped))
        A("")
        A("| Thème | Sujet | Indicateur | Priorité | Fiabilité |")
        A("|---|---|---|---|---|")
        for theme, sujet, k in scoped:
            flab, _ = FIAB_LABEL.get(k.get("fiabilite", "inconnue"), ("?", "?"))
            A("| %s | %s | %s | %s | %s |" % (
                md_escape(theme), md_escape(sujet), md_escape(k["indicateur"]),
                k.get("priorite") or "—", flab))
        A("")
    else:
        A("_Aucun indicateur dans ce périmètre — élargir le scope ou renseigner "
          "des priorités dans le Matrice.xlsx._")
        A("")

    # Alertes fiabilité
    alerts = []
    for t in themes:
        for s in t["sujets"]:
            for k in s["kpis"]:
                if k.get("fiabilite") in ("partielle", "inconnue"):
                    alerts.append((t["theme"], s["sujet"], k))
    A("## Alertes fiabilité")
    A("")
    if alerts:
        A("Indicateurs à fiabilité partielle ou source non identifiée — signalés "
          "par un marqueur (`*`/`◆`) sur la maquette :")
        A("")
        A("| Indicateur | Fiabilité | Système source | Source données | Raison |")
        A("|---|---|---|---|---|")
        for theme, sujet, k in alerts:
            flab, tag = FIAB_LABEL.get(k["fiabilite"], ("?", "?"))
            if k["fiabilite"] == "inconnue":
                raison = "Source non identifiée" if not k.get("source_donnees") \
                    else "Fiabilité inconnue"
            else:
                raison = "Fiabilité partielle / à valider"
            A("| %s | %s (%s) | %s | %s | %s |" % (
                md_escape(k["indicateur"]), flab, tag,
                md_escape(k.get("systeme_source", "")) or "—",
                md_escape(k.get("source_donnees", "")) or "—", raison))
        A("")
    else:
        A("_Aucune alerte : tous les indicateurs disposent d'une source fiable._")
        A("")

    A("---")
    A("*Document généré par `generate-cadrage.py` — ne pas éditer à la main.*")

    out = os.path.join(cdir, "cadrage.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    sys.stderr.write("OK: %s généré (%d indicateurs cadrés, %d dans la maquette, "
                     "%d alertes fiabilité).\n"
                     % (out, stats.get("total", 0), len(scoped), len(alerts)))


if __name__ == "__main__":
    main()
