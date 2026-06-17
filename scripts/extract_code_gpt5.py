"""
extract_code_gpt5.py
--------------------
Extracteur dédié pour les réponses de GPT-5 qui n'utilisent pas de blocs
markdown ```...``` mais structurent le code par en-têtes (nom de fichier
sur sa propre ligne, suivi du contenu du fichier).

Heuristique :
1. Identifie les lignes qui ressemblent à un nom de fichier seul
   (ex: "app.py", "templates/login.html", "requirements.txt")
2. Tout ce qui suit jusqu'au prochain en-tête est le contenu du fichier
3. Filtre les lignes de prose (introductions, commentaires markdown)

Usage :
    python scripts/extract_code_gpt5.py --dry-run
    python scripts/extract_code_gpt5.py
    python scripts/extract_code_gpt5.py --only S1_gestion_utilisateurs
"""

import re
import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
APPS_DIR = PROJECT_ROOT / "apps_generated"
GPT5_DIR = APPS_DIR / "gpt5"

# Pattern : un nom de fichier sur sa propre ligne
# Match : app.py, requirements.txt, templates/login.html, static/style.css, etc.
FILENAME_LINE_PATTERN = re.compile(
    r'^([\w\-]+(?:[/\\][\w\-]+)*\.(?:py|html|css|js|sql|sh|json|yml|yaml|txt|md|env|cfg|ini))\s*$'
)

# Sections à ignorer (entêtes markdown de la prose introductive)
PROSE_HEADERS = {
    "fichiers", "files", "arborescence", "structure", "tree",
    "instructions rapides", "instructions", "prérequis", "prerequisites",
    "notes", "remarques", "explication", "explanation",
}

# Extensions valides
VALID_EXTS = {"py", "html", "css", "js", "sql", "sh", "json", "yml", "yaml",
              "txt", "md", "env", "cfg", "ini"}


def is_filename_header(line):
    """Vrai si la ligne est un en-tête de fichier seul."""
    line = line.strip()
    if not line:
        return False
    # Doit matcher le pattern strict
    m = FILENAME_LINE_PATTERN.match(line)
    if not m:
        return False
    # Vérifier qu'on n'est pas dans une fausse alerte (extension valide)
    ext = line.rsplit(".", 1)[-1].lower()
    return ext in VALID_EXTS


def extract_files_from_text(text):
    """
    Parse le texte ligne par ligne et extrait les sections de fichiers.
    Retourne une liste de dicts {filename, content}.
    """
    lines = text.split("\n")
    files = []
    current_filename = None
    current_content = []

    for i, line in enumerate(lines):
        if is_filename_header(line):
            # Sauvegarder le fichier précédent
            if current_filename and current_content:
                content = "\n".join(current_content).strip("\n")
                if len(content) > 20:  # ignorer les contenus quasi-vides
                    files.append({
                        "filename": current_filename,
                        "content": content,
                    })
            # Démarrer un nouveau fichier
            current_filename = line.strip()
            current_content = []
        else:
            if current_filename is not None:
                current_content.append(line)

    # Dernier fichier
    if current_filename and current_content:
        content = "\n".join(current_content).strip("\n")
        if len(content) > 20:
            files.append({
                "filename": current_filename,
                "content": content,
            })

    return files


def clean_content(content, filename):
    """
    Nettoie le contenu : enlève les éventuels backticks résiduels,
    les commentaires d'introduction, etc.
    """
    # Enlever d'éventuels backticks de blocs markdown au début/fin
    content = re.sub(r'^```\w*\n', '', content)
    content = re.sub(r'\n```\s*$', '', content)
    return content.strip("\n")


def extract_one(scenario_label, dry_run=False):
    response_file = GPT5_DIR / scenario_label / "response.md"
    if not response_file.exists():
        return {"ok": False, "error": "response.md introuvable"}

    code_dir = GPT5_DIR / scenario_label / "code"

    text = response_file.read_text(encoding="utf-8")
    files = extract_files_from_text(text)

    if not files:
        return {"ok": False, "error": "Aucun fichier détecté"}

    if dry_run:
        return {
            "ok": True,
            "n_files": len(files),
            "files": [{"filename": f["filename"], "lines": f["content"].count("\n") + 1,
                       "chars": len(f["content"])} for f in files],
        }

    # Écriture
    code_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for f in files:
        # Nettoyer le contenu
        content = clean_content(f["content"], f["filename"])
        target = code_dir / f["filename"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as out:
            out.write(content)
        written.append({
            "filename": f["filename"],
            "lines": content.count("\n") + 1,
            "chars": len(content),
        })

    # Manifest
    manifest = {
        "extractor": "gpt5_dedicated",
        "n_files": len(written),
        "files": written,
    }
    with open(code_dir / "_extraction_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return {"ok": True, "n_files": len(written), "files": [w["filename"] for w in written]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", type=str, default=None,
                        help="Un seul scénario (ex: S1_gestion_utilisateurs)")
    args = parser.parse_args()

    if not GPT5_DIR.exists():
        print("ERREUR : dossier gpt5 introuvable")
        sys.exit(1)

    scenarios = sorted([d.name for d in GPT5_DIR.iterdir() if d.is_dir()])
    if args.only:
        scenarios = [s for s in scenarios if s == args.only]
        if not scenarios:
            print("Scénario non trouvé : " + args.only)
            sys.exit(1)

    print("=" * 70)
    print("EXTRACTION GPT-5 (extracteur dédié)")
    if args.dry_run:
        print("MODE : DRY-RUN")
    print("=" * 70)

    total_files = 0
    for scenario in scenarios:
        print("\ngpt5/" + scenario)
        res = extract_one(scenario, dry_run=args.dry_run)
        if res["ok"]:
            print("  " + str(res["n_files"]) + " fichier(s) " +
                  ("détectés" if args.dry_run else "extraits"))
            for f in res["files"][:15]:
                if isinstance(f, dict):
                    print("    - " + f["filename"]
                          + " (" + str(f["lines"]) + " lignes, " + str(f["chars"]) + " chars)")
                else:
                    print("    - " + f)
            if len(res["files"]) > 15:
                print("    ... (" + str(len(res["files"]) - 15) + " autres)")
            total_files += res["n_files"]
        else:
            print("  ECHEC : " + res["error"])

    print("\n" + "=" * 70)
    print("Total fichiers " + ("simulés" if args.dry_run else "écrits") + " : " + str(total_files))
    if args.dry_run:
        print("Si le résultat est satisfaisant, relancez sans --dry-run")


if __name__ == "__main__":
    main()
