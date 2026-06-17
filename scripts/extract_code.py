"""
extract_code.py
---------------
Extrait les fichiers de code (Python, HTML, CSS, JS, SQL...) depuis les
réponses markdown des LLMs sauvegardées dans apps_generated/<model>/<scenario>/response.md

Stratégie :
1. Détecte tous les blocs de code ```...```
2. Pour chaque bloc, essaie de trouver un nom de fichier dans :
   - Le titre markdown qui précède (## app.py, ### templates/index.html)
   - La première ligne du bloc (# app.py, // app.js, <!-- index.html -->)
   - Le texte courant juste avant le bloc
3. Si aucun nom détecté, génère un nom basé sur le langage et un compteur
4. Crée l'arborescence dans apps_generated/<model>/<scenario>/code/

Usage :
    python scripts/extract_code.py                              # Extrait tout
    python scripts/extract_code.py --only claude_opus           # Un seul modèle
    python scripts/extract_code.py --only claude_opus --scenario S1_gestion_utilisateurs
    python scripts/extract_code.py --report                     # Affiche un rapport sans extraire
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
APPS_DIR = PROJECT_ROOT / "apps_generated"

# Mapping langage -> extension par défaut
LANG_TO_EXT = {
    "python": "py", "py": "py",
    "html": "html",
    "css": "css",
    "javascript": "js", "js": "js",
    "sql": "sql",
    "bash": "sh", "shell": "sh", "sh": "sh",
    "json": "json",
    "yaml": "yml", "yml": "yml",
    "jinja": "html", "jinja2": "html",
    "text": "txt", "txt": "txt",
    "": "txt",
}

# Patterns pour détecter un nom de fichier
FILENAME_PATTERNS = [
    # Commentaire Python : # app.py  ou  # File: app.py  ou  # filename: app.py
    re.compile(r'^\s*#\s*(?:[Ff]ile(?:name)?\s*:\s*)?([\w\-./\\]+\.\w+)\s*$', re.MULTILINE),
    # Commentaire HTML : <!-- index.html -->
    re.compile(r'^\s*<!--\s*([\w\-./\\]+\.\w+)\s*-->\s*$', re.MULTILINE),
    # Commentaire JS/CSS : // app.js  ou  /* app.css */
    re.compile(r'^\s*(?://|/\*)\s*([\w\-./\\]+\.\w+)\s*(?:\*/)?\s*$', re.MULTILINE),
]

# Pattern pour trouver un nom de fichier dans le texte qui précède un bloc
# Ex: "Voici le fichier app.py :", "## templates/index.html", "**static/style.css**"
PRECEDING_TEXT_PATTERN = re.compile(
    r'(?:^|\s|`|\*\*|##\s)([\w\-]+(?:[/\\][\w\-]+)*\.(?:py|html|css|js|sql|sh|json|yml|yaml|txt|md|env|cfg|ini))(?:`|\*\*|\s|:|$)',
    re.IGNORECASE
)

# Pattern principal pour les blocs de code
CODE_BLOCK_PATTERN = re.compile(
    r'```(\w*)\n(.*?)```',
    re.DOTALL
)


def safe_filename(name):
    """Nettoie un nom de fichier pour qu'il soit sûr."""
    # Remplacer les backslashes Windows par des slashes Unix
    name = name.replace("\\", "/")
    # Enlever les chemins absolus ou parents
    name = name.lstrip("/")
    name = name.replace("../", "").replace("..\\", "")
    # Garder seulement chars alphanumériques + . - _ /
    name = re.sub(r'[^\w\-./]', '_', name)
    return name


def detect_filename_in_block(code_text, lang):
    """Cherche un nom de fichier dans les premières lignes du bloc."""
    # Examiner les 3 premières lignes seulement
    lines = code_text.split("\n")[:3]
    for line in lines:
        for pattern in FILENAME_PATTERNS:
            m = pattern.search(line)
            if m:
                return m.group(1).strip()
    return None


def detect_filename_before_block(text_before, lookback_chars=300):
    """Cherche un nom de fichier dans le texte qui précède le bloc."""
    # Examiner seulement les derniers caractères avant le bloc
    snippet = text_before[-lookback_chars:] if len(text_before) > lookback_chars else text_before
    matches = PRECEDING_TEXT_PATTERN.findall(snippet)
    if matches:
        # Prendre la dernière mention (la plus proche du bloc)
        return matches[-1]
    return None


def extract_blocks(markdown_text):
    """
    Extrait tous les blocs de code avec leurs métadonnées.
    Retourne une liste de dicts {lang, code, filename, source}.
    """
    blocks = []
    counters = {}  # Compteurs par langage pour les fichiers anonymes

    for match in CODE_BLOCK_PATTERN.finditer(markdown_text):
        lang = (match.group(1) or "").lower().strip()
        code = match.group(2)
        text_before = markdown_text[:match.start()]

        # Méthode 1 : nom dans le bloc (commentaire en première ligne)
        filename = detect_filename_in_block(code, lang)
        source = "in_block"

        # Méthode 2 : nom dans le texte précédent
        if not filename:
            filename = detect_filename_before_block(text_before)
            if filename:
                source = "preceding_text"

        # Méthode 3 : nom généré
        if not filename:
            ext = LANG_TO_EXT.get(lang, "txt")
            counters[ext] = counters.get(ext, 0) + 1
            filename = "fragment_" + str(counters[ext]) + "." + ext
            source = "generated"

        blocks.append({
            "lang": lang,
            "code": code,
            "filename": safe_filename(filename),
            "source": source,
        })

    return blocks


def merge_duplicate_filenames(blocks):
    """
    Si plusieurs blocs ont le même filename, on les concatène (pour les cas où
    un LLM split un fichier en plusieurs blocs avec '...' au milieu).
    Sauf si ce sont des fragments générés différents.
    """
    by_name = {}
    order = []
    for block in blocks:
        name = block["filename"]
        if name in by_name:
            # Concaténer (avec un séparateur visible)
            by_name[name]["code"] += "\n# --- bloc suivant fusionné ---\n" + block["code"]
            by_name[name]["merged"] = True
        else:
            by_name[name] = block
            order.append(name)
    return [by_name[name] for name in order]


def extract_one(model_label, scenario_label, dry_run=False):
    """Extrait le code pour une génération."""
    response_file = APPS_DIR / model_label / scenario_label / "response.md"
    if not response_file.exists():
        return {"ok": False, "error": "response.md introuvable"}

    code_dir = APPS_DIR / model_label / scenario_label / "code"

    with open(response_file, "r", encoding="utf-8") as f:
        markdown = f.read()

    blocks = extract_blocks(markdown)
    blocks = merge_duplicate_filenames(blocks)

    if not blocks:
        return {"ok": False, "error": "Aucun bloc de code détecté"}

    # Stats
    by_source = {"in_block": 0, "preceding_text": 0, "generated": 0}
    for b in blocks:
        by_source[b["source"]] = by_source.get(b["source"], 0) + 1

    if dry_run:
        return {
            "ok": True,
            "n_blocks": len(blocks),
            "by_source": by_source,
            "files": [b["filename"] for b in blocks],
        }

    # Écriture
    code_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for b in blocks:
        target = code_dir / b["filename"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(b["code"])
        written.append(str(target.relative_to(code_dir)))

    # Sauvegarder un manifest
    manifest = {
        "n_blocks": len(blocks),
        "by_source": by_source,
        "files": [
            {
                "filename": b["filename"],
                "lang": b["lang"],
                "source": b["source"],
                "lines": b["code"].count("\n") + 1,
                "chars": len(b["code"]),
            }
            for b in blocks
        ],
    }
    with open(code_dir / "_extraction_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return {
        "ok": True,
        "n_blocks": len(blocks),
        "by_source": by_source,
        "files": written,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str, default=None,
                        help="Ne traite que ce modèle (ex: claude_opus)")
    parser.add_argument("--scenario", type=str, default=None,
                        help="Ne traite que ce scénario")
    parser.add_argument("--report", action="store_true",
                        help="Affiche un rapport sans écrire les fichiers")
    args = parser.parse_args()

    if not APPS_DIR.exists():
        print("ERREUR : dossier introuvable : " + str(APPS_DIR))
        sys.exit(1)

    # Trouver toutes les générations
    tasks = []
    for model_dir in sorted(APPS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        if args.only and model_dir.name != args.only:
            continue
        for scenario_dir in sorted(model_dir.iterdir()):
            if not scenario_dir.is_dir():
                continue
            if args.scenario and scenario_dir.name != args.scenario:
                continue
            if (scenario_dir / "response.md").exists():
                tasks.append((model_dir.name, scenario_dir.name))

    if not tasks:
        print("Aucune génération trouvée à traiter")
        sys.exit(0)

    print("=" * 70)
    print("EXTRACTION DU CODE")
    print("=" * 70)
    print("Génération(s) à traiter : " + str(len(tasks)))
    if args.report:
        print("Mode : RAPPORT (pas d'écriture)")
    print("=" * 70)

    results = []
    n_ok = 0
    n_err = 0
    total_blocks = 0
    total_files = 0

    for model_label, scenario_label in tasks:
        print("\n" + model_label + " / " + scenario_label)
        res = extract_one(model_label, scenario_label, dry_run=args.report)

        if res["ok"]:
            n_ok += 1
            total_blocks += res["n_blocks"]
            total_files += len(res["files"])
            print("  " + str(res["n_blocks"]) + " bloc(s) extrait(s) -> "
                  + str(len(res["files"])) + " fichier(s) après fusion")
            print("  Sources : "
                  + str(res["by_source"]["in_block"]) + " in-block, "
                  + str(res["by_source"]["preceding_text"]) + " preceding-text, "
                  + str(res["by_source"]["generated"]) + " generated")

            # Afficher les fichiers extraits
            for filename in res["files"][:8]:
                print("    - " + filename)
            if len(res["files"]) > 8:
                print("    ... (" + str(len(res["files"]) - 8) + " autres)")
        else:
            n_err += 1
            print("  ECHEC : " + res["error"])

        results.append((model_label, scenario_label, res))

    # Synthèse
    print("\n" + "=" * 70)
    print("SYNTHÈSE")
    print("=" * 70)
    print("Réussites : " + str(n_ok) + "/" + str(len(tasks)))
    print("Échecs    : " + str(n_err))
    print("Total blocs détectés : " + str(total_blocks))
    print("Total fichiers écrits : " + str(total_files))

    # Diagnostic des cas problématiques
    too_few = [(m, s, r) for m, s, r in results if r.get("ok") and r["n_blocks"] <= 2]
    if too_few:
        print("\n[Attention] Générations avec très peu de blocs (peut-être code monolithique) :")
        for m, s, r in too_few:
            print("  - " + m + " / " + s + " : " + str(r["n_blocks"]) + " bloc(s)")

    many_generated = [(m, s, r) for m, s, r in results
                      if r.get("ok") and r["by_source"].get("generated", 0) > 3]
    if many_generated:
        print("\n[Attention] Générations avec beaucoup de noms générés (extraction imparfaite) :")
        for m, s, r in many_generated:
            print("  - " + m + " / " + s + " : "
                  + str(r["by_source"]["generated"]) + " fichiers anonymes")


if __name__ == "__main__":
    main()
