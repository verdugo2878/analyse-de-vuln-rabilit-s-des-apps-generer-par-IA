"""
diagnose_extraction.py
----------------------
Analyse l'état de l'extraction après run de extract_code.py.

Identifie :
- Les générations sans extraction (0 blocs)
- Les fichiers anonymes (fragment_X.*) qui sont en réalité du code identifiable
- Les apps sans aucun .py (très suspect)
- Les fichiers textuels qui contiennent en fait du code Python

Usage :
    python scripts/diagnose_extraction.py
"""

import os
import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
APPS_DIR = PROJECT_ROOT / "apps_generated"

# Indices forts qu'un fichier "anonyme" est en réalité du Python Flask
PYTHON_INDICATORS = [
    "from flask import",
    "import flask",
    "@app.route",
    "Flask(__name__)",
    "def __init__",
    "if __name__ == '__main__'",
]

HTML_INDICATORS = [
    "<!DOCTYPE",
    "<html",
    "{% extends",
    "{% block",
    "{{ url_for",
]

SQL_INDICATORS = [
    "CREATE TABLE",
    "INSERT INTO",
    "SELECT ",
]


def detect_real_lang(content):
    """Devine le vrai langage d'un fichier basé sur son contenu."""
    sample = content[:2000].lower()
    score_py = sum(1 for ind in PYTHON_INDICATORS if ind.lower() in sample)
    score_html = sum(1 for ind in HTML_INDICATORS if ind.lower() in sample)
    score_sql = sum(1 for ind in SQL_INDICATORS if ind.lower() in sample)

    if score_py >= 2:
        return "python"
    if score_html >= 2:
        return "html"
    if score_sql >= 2:
        return "sql"
    if score_py == 1:
        return "python?"
    if score_html == 1:
        return "html?"
    return "?"


def main():
    print("=" * 70)
    print("DIAGNOSTIC DE L'EXTRACTION")
    print("=" * 70)

    no_extraction = []   # Générations sans dossier code/ ou code/ vide
    no_python = []       # Générations sans aucun .py
    misnamed = []        # Fichiers anonymes qui sont en réalité du code identifiable
    summary = []         # Stats par génération

    for model_dir in sorted(APPS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        for scenario_dir in sorted(model_dir.iterdir()):
            if not scenario_dir.is_dir():
                continue

            response = scenario_dir / "response.md"
            code_dir = scenario_dir / "code"

            if not response.exists():
                continue

            label = model_dir.name + "/" + scenario_dir.name

            # Pas de dossier code = échec d'extraction
            if not code_dir.exists():
                no_extraction.append(label)
                continue

            # Compter par extension
            files = [f for f in code_dir.rglob("*") if f.is_file() and not f.name.startswith("_")]
            if not files:
                no_extraction.append(label)
                continue

            n_py = sum(1 for f in files if f.suffix == ".py")
            n_html = sum(1 for f in files if f.suffix == ".html")
            n_anon = sum(1 for f in files if f.name.startswith("fragment_"))

            if n_py == 0:
                no_python.append(label)

            # Vérifier les fichiers anonymes
            for f in files:
                if f.name.startswith("fragment_"):
                    try:
                        content = f.read_text(encoding="utf-8", errors="ignore")
                        real_lang = detect_real_lang(content)
                        if real_lang in ("python", "html", "sql"):
                            misnamed.append({
                                "path": str(f.relative_to(APPS_DIR)),
                                "current_ext": f.suffix,
                                "detected": real_lang,
                                "size": len(content),
                            })
                    except Exception:
                        pass

            summary.append({
                "label": label,
                "n_files": len(files),
                "n_py": n_py,
                "n_html": n_html,
                "n_anon": n_anon,
            })

    # === RAPPORTS ===
    print("\n--- Générations sans extraction (0 fichier dans code/) ---")
    if no_extraction:
        for l in no_extraction:
            print("  - " + l)
    else:
        print("  (aucune)")

    print("\n--- Générations sans aucun fichier .py ---")
    if no_python:
        for l in no_python:
            print("  - " + l)
    else:
        print("  (aucune)")

    print("\n--- Fichiers anonymes mal classés (en réalité du code identifiable) ---")
    if misnamed:
        for m in misnamed:
            print("  - " + m["path"]
                  + " (ext " + m["current_ext"]
                  + " mais c'est du " + m["detected"]
                  + ", " + str(m["size"]) + " chars)")
    else:
        print("  (aucun)")

    # === STATS GLOBALES ===
    print("\n--- Statistiques par génération (top 30) ---")
    print(f"  {'Génération':<50} {'Total':>6} {'PY':>4} {'HTML':>5} {'Anon':>5}")
    for s in summary[:30]:
        print(f"  {s['label']:<50} {s['n_files']:>6} {s['n_py']:>4} {s['n_html']:>5} {s['n_anon']:>5}")

    total_files = sum(s["n_files"] for s in summary)
    total_py = sum(s["n_py"] for s in summary)
    total_html = sum(s["n_html"] for s in summary)
    total_anon = sum(s["n_anon"] for s in summary)

    print("\n--- TOTAUX ---")
    print("  Générations OK : " + str(len(summary)))
    print("  Fichiers totaux : " + str(total_files))
    print("  Fichiers .py   : " + str(total_py))
    print("  Fichiers .html : " + str(total_html))
    print("  Fragments anonymes : " + str(total_anon))


if __name__ == "__main__":
    main()
