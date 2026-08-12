#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cache du contrat DATA normalisé (module partagé — pas un script autonome).

Pourquoi ce module existe
-------------------------
`extract-data.py` re-parse intégralement `donnees.xlsx` à chaque appel
(plusieurs secondes sur un gros classeur). Or le skill lance l'extracteur
jusqu'à 3 fois par client : auto-contrôle de `generate-data.py`, puis
`render.py`, puis `generate-pitch.py` (et `build-views.py`). Le xlsx ne
change pas entre ces appels : ce module mémorise le contrat DATA dans
`clients/<client>/.data-cache.json` et le réutilise tant que le xlsx
(et le manifeste éventuel) n'ont pas changé (signature = chemins + mtime).

API :
    import data_cache
    data = data_cache.get_data(xlsx_path, manifest=None)   # dict parsé
    lit  = data_cache.literal(data)                        # littéral JS compact

Le cache est best-effort : toute erreur de lecture/écriture retombe sur une
exécution directe de l'extracteur.
"""
import sys
import os
import re
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACTOR = os.path.join(HERE, "extract-data.py")
CACHE_NAME = ".data-cache.json"


def _signature(xlsx, manifest):
    sig = {"xlsx": os.path.abspath(xlsx),
           "xlsx_mtime": os.path.getmtime(xlsx),
           "xlsx_size": os.path.getsize(xlsx),
           "manifest": None, "manifest_mtime": None}
    if manifest and os.path.exists(manifest):
        sig["manifest"] = os.path.abspath(manifest)
        sig["manifest_mtime"] = os.path.getmtime(manifest)
    return sig


def _run_extractor(xlsx, manifest=None):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    cmd = [sys.executable, EXTRACTOR, xlsx]
    if manifest and os.path.exists(manifest):
        cmd += ["--manifest", manifest]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                         errors="replace", env=env)
    sys.stderr.write(out.stderr or "")
    if out.returncode != 0:
        raise SystemExit("ERREUR: extract-data.py a échoué.")
    m = re.search(r"const DATA = (\{.*\});\s*$", out.stdout, re.S)
    if not m:
        raise SystemExit("ERREUR: bloc DATA introuvable dans la sortie de l'extracteur.")
    return json.loads(m.group(1))


def get_data(xlsx, manifest=None, use_cache=True):
    """Retourne le contrat DATA (dict) du classeur, via cache si valide."""
    sig = _signature(xlsx, manifest)
    cache = os.path.join(os.path.dirname(sig["xlsx"]), CACHE_NAME)
    if use_cache and os.path.exists(cache):
        try:
            c = json.load(open(cache, encoding="utf-8"))
            if c.get("sig") == sig:
                return c["data"]
        except Exception:
            pass
    data = _run_extractor(xlsx, manifest)
    try:
        with open(cache, "w", encoding="utf-8") as f:
            json.dump({"sig": sig, "data": data}, f, ensure_ascii=False)
    except Exception:
        pass
    return data


def literal(data):
    """Sérialisation identique à emit_normalized() de l'extracteur (compacte)."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
