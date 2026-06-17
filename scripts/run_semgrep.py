"""
run_semgrep.py
--------------
Exécute Semgrep sur les 22 applications extraites et consolide les résultats.

Configuration retenue (gratuit, sans authentification) :
  - p/owasp-top-ten : couverture OWASP 2021
  - p/flask         : règles spécifiques Flask
  - p/xss           : XSS dans templates et code

Sorties :
- analyses/static/semgrep/<model>/<scenario>.json   (rapport JSON brut par app)
- analyses/static/semgrep_consolidated.csv          (un finding par ligne)
- analyses/static/semgrep_summary.csv               (synthèse par génération)
- analyses/static/semgrep_summary.txt               (synthèse lisible)

Usage :
    python scripts/run_semgrep.py
    python scripts/run_semgrep.py --only claude_opus
    python scripts/run_semgrep.py --skip-run    # consolider les JSON déjà générés
"""

import os
import sys
import json
import csv
import argparse
import subprocess
import time
from pathlib import Path
from collections import defaultdict, Counter

PROJECT_ROOT = Path(__file__).parent.parent
APPS_DIR = PROJECT_ROOT / "apps_generated"
ANALYSES_DIR = PROJECT_ROOT / "analyses" / "static"
SEMGREP_DIR = ANALYSES_DIR / "semgrep"

# Configuration retenue après tests
SEMGREP_CONFIGS = [
    "p/owasp-top-ten",
    "p/flask",
    "p/xss",
]


def run_semgrep_on(app_dir, output_file):
    """Exécute Semgrep en JSON sur un dossier code/ et sauvegarde le résultat."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["semgrep"]
    for config in SEMGREP_CONFIGS:
        cmd.extend(["--config", config])
    cmd.extend([
        "--json",
        "--output", str(output_file),
        "--no-git-ignore",
        "--metrics=off",
        "--quiet",
        str(app_dir),
    ])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        # Semgrep retourne 1 quand il trouve des findings, c'est normal
        # Code 0 = aucun finding, 1 = findings, autres = vraies erreurs
        if result.returncode in (0, 1):
            return {"ok": True}
        else:
            return {
                "ok": False,
                "error": "code=" + str(result.returncode) + " : " + (result.stderr[:300] if result.stderr else "")
            }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout (300s)"}
    except FileNotFoundError:
        return {"ok": False, "error": "semgrep non installé. Faire : pip install semgrep"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def parse_semgrep_json(json_file):
    """Parse un rapport Semgrep JSON et retourne la liste des findings + métriques."""
    if not json_file.exists():
        return [], {}

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [], {"parse_error": str(e)}

    findings = []
    for r in data.get("results", []):
        extra = r.get("extra", {}) or {}
        metadata = extra.get("metadata", {}) or {}

        # Extraction des CWE et OWASP (formats variables)
        cwe_raw = metadata.get("cwe", "")
        if isinstance(cwe_raw, list):
            cwe = "; ".join(str(c) for c in cwe_raw)
        else:
            cwe = str(cwe_raw)

        owasp_raw = metadata.get("owasp", "")
        if isinstance(owasp_raw, list):
            owasp = "; ".join(str(o) for o in owasp_raw)
        else:
            owasp = str(owasp_raw)

        findings.append({
            "check_id": r.get("check_id", ""),
            "message": (extra.get("message", "") or "")[:300],
            "severity": extra.get("severity", ""),
            "cwe": cwe,
            "owasp": owasp,
            "category": metadata.get("category", ""),
            "technology": "; ".join(metadata.get("technology", [])) if isinstance(metadata.get("technology"), list) else str(metadata.get("technology", "")),
            "filename": r.get("path", ""),
            "line_start": (r.get("start", {}) or {}).get("line", 0),
            "line_end": (r.get("end", {}) or {}).get("line", 0),
        })

    # Métriques globales
    paths = data.get("paths", {})
    metrics = {
        "scanned_count": len(paths.get("scanned", [])),
    }

    return findings, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str, default=None,
                        help="Un seul modèle (ex: claude_opus)")
    parser.add_argument("--scenario", type=str, default=None,
                        help="Un seul scénario")
    parser.add_argument("--skip-run", action="store_true",
                        help="Ne pas relancer Semgrep, juste consolider les JSON existants")
    args = parser.parse_args()

    if not APPS_DIR.exists():
        print("ERREUR : dossier apps_generated introuvable")
        sys.exit(1)

    # Lister les générations à analyser
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
            code_dir = scenario_dir / "code"
            if not code_dir.exists():
                continue
            # Vérifier qu'il y a au moins un fichier source
            files = list(code_dir.rglob("*.py")) + list(code_dir.rglob("*.html"))
            if not files:
                print("[skip] " + model_dir.name + "/" + scenario_dir.name + " : aucun fichier")
                continue
            tasks.append((model_dir.name, scenario_dir.name, code_dir))

    print("=" * 70)
    print("ANALYSE SEMGREP")
    print("=" * 70)
    print("Configuration : " + ", ".join(SEMGREP_CONFIGS))
    print("Applications à analyser : " + str(len(tasks)))
    print("=" * 70)

    # Étape 1 : Exécution
    if not args.skip_run:
        for i, (model, scenario, code_dir) in enumerate(tasks, 1):
            output_file = SEMGREP_DIR / model / (scenario + ".json")
            print("[" + str(i) + "/" + str(len(tasks)) + "] "
                  + model + "/" + scenario + " ... ", end="", flush=True)
            start = time.time()
            res = run_semgrep_on(code_dir, output_file)
            elapsed = time.time() - start
            if res["ok"]:
                print("OK (" + str(round(elapsed, 1)) + "s)")
            else:
                print("ECHEC : " + res.get("error", "?"))

    # Étape 2 : Consolidation
    print("\nConsolidation...")
    all_findings = []
    summary_rows = []

    for model, scenario, code_dir in tasks:
        json_file = SEMGREP_DIR / model / (scenario + ".json")
        findings, metrics = parse_semgrep_json(json_file)

        for f in findings:
            f["model"] = model
            f["scenario"] = scenario
            try:
                rel = Path(f["filename"]).relative_to(code_dir)
                f["filename_relative"] = str(rel)
            except (ValueError, TypeError):
                f["filename_relative"] = f["filename"]
            all_findings.append(f)

        # Comptage par sévérité (Semgrep utilise INFO/WARNING/ERROR)
        sev_counter = Counter(f["severity"] for f in findings)
        rule_counter = Counter(f["check_id"] for f in findings)

        summary_rows.append({
            "model": model,
            "scenario": scenario,
            "n_files_scanned": metrics.get("scanned_count", 0),
            "n_findings": len(findings),
            "n_error": sev_counter.get("ERROR", 0),
            "n_warning": sev_counter.get("WARNING", 0),
            "n_info": sev_counter.get("INFO", 0),
            "top_rules": ";".join([r.split(".")[-1] + "(" + str(c) + ")"
                                   for r, c in rule_counter.most_common(3)]),
        })

    # CSV consolidé
    findings_csv = ANALYSES_DIR / "semgrep_consolidated.csv"
    if all_findings:
        with open(findings_csv, "w", encoding="utf-8", newline="") as f:
            fieldnames = ["model", "scenario", "check_id", "severity", "cwe", "owasp",
                          "category", "technology", "filename_relative",
                          "line_start", "line_end", "message"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for fd in all_findings:
                writer.writerow(fd)
        print("  -> " + str(findings_csv) + " (" + str(len(all_findings)) + " findings)")

    # CSV summary
    summary_csv = ANALYSES_DIR / "semgrep_summary.csv"
    with open(summary_csv, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["model", "scenario", "n_files_scanned", "n_findings",
                      "n_error", "n_warning", "n_info", "top_rules"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)
    print("  -> " + str(summary_csv))

    # TXT summary lisible
    summary_txt = ANALYSES_DIR / "semgrep_summary.txt"
    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("SYNTHESE SEMGREP\n")
        f.write("Configuration : " + ", ".join(SEMGREP_CONFIGS) + "\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"{'Modèle/Scénario':<45} {'Files':>6} {'Total':>6} {'ERR':>4} {'WARN':>5} {'INFO':>5}\n")
        f.write("-" * 80 + "\n")
        for r in summary_rows:
            label = r["model"] + "/" + r["scenario"]
            f.write(f"{label:<45} {r['n_files_scanned']:>6} {r['n_findings']:>6} "
                    f"{r['n_error']:>4} {r['n_warning']:>5} {r['n_info']:>5}\n")

        # Agrégation par modèle
        f.write("\n" + "=" * 80 + "\n")
        f.write("AGREGATION PAR MODELE\n")
        f.write("=" * 80 + "\n\n")
        by_model = defaultdict(lambda: {"n_files_scanned": 0, "n_findings": 0,
                                          "n_error": 0, "n_warning": 0, "n_info": 0})
        for r in summary_rows:
            m = by_model[r["model"]]
            m["n_files_scanned"] += r["n_files_scanned"]
            m["n_findings"] += r["n_findings"]
            m["n_error"] += r["n_error"]
            m["n_warning"] += r["n_warning"]
            m["n_info"] += r["n_info"]

        f.write(f"{'Modèle':<20} {'Files':>8} {'Findings':>10} {'ERR':>5} {'WARN':>5} {'INFO':>5}\n")
        f.write("-" * 65 + "\n")
        for model, m in sorted(by_model.items()):
            f.write(f"{model:<20} {m['n_files_scanned']:>8} {m['n_findings']:>10} "
                    f"{m['n_error']:>5} {m['n_warning']:>5} {m['n_info']:>5}\n")

        # Top règles
        f.write("\n" + "=" * 80 + "\n")
        f.write("TOP 15 DES REGLES SEMGREP LES PLUS DECLENCHEES\n")
        f.write("=" * 80 + "\n\n")
        rule_counter = Counter(fd["check_id"] for fd in all_findings)
        for rule, count in rule_counter.most_common(15):
            short_rule = rule.split(".")[-1] if "." in rule else rule
            f.write(f"  {count:>4}× {short_rule}\n")
            f.write(f"        ({rule})\n")

        # Top OWASP
        f.write("\n" + "=" * 80 + "\n")
        f.write("DISTRIBUTION OWASP\n")
        f.write("=" * 80 + "\n\n")
        owasp_counter = Counter(fd["owasp"] for fd in all_findings if fd["owasp"])
        for owasp, count in owasp_counter.most_common(10):
            f.write(f"  {count:>4}× {owasp}\n")

        # Top CWE
        f.write("\n" + "=" * 80 + "\n")
        f.write("DISTRIBUTION CWE\n")
        f.write("=" * 80 + "\n\n")
        cwe_counter = Counter(fd["cwe"] for fd in all_findings if fd["cwe"])
        for cwe, count in cwe_counter.most_common(15):
            f.write(f"  {count:>4}× {cwe}\n")

    print("  -> " + str(summary_txt))

    # Affichage console
    print("\n" + "=" * 70)
    print("RESUME RAPIDE")
    print("=" * 70)
    print("Total findings : " + str(len(all_findings)))
    sev_total = Counter(fd["severity"] for fd in all_findings)
    print("  ERROR   : " + str(sev_total.get("ERROR", 0)))
    print("  WARNING : " + str(sev_total.get("WARNING", 0)))
    print("  INFO    : " + str(sev_total.get("INFO", 0)))

    by_model_count = Counter(fd["model"] for fd in all_findings)
    print("\nPar modèle :")
    for model in sorted(set(t[0] for t in tasks)):
        print("  " + model + " : " + str(by_model_count.get(model, 0)) + " findings")


if __name__ == "__main__":
    main()
