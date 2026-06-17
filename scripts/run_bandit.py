"""
run_bandit.py
-------------
Exécute Bandit sur les 22 applications extraites et consolide les résultats.

Sorties :
- analyses/static/bandit/<model>/<scenario>.json    (rapport JSON brut par app)
- analyses/static/bandit_consolidated.csv           (un CSV avec un finding par ligne)
- analyses/static/bandit_summary.csv                (synthèse par modèle/scénario)
- analyses/static/bandit_summary.txt                (synthèse lisible)

Usage :
    python scripts/run_bandit.py
    python scripts/run_bandit.py --only claude_opus
"""

import os
import sys
import json
import csv
import argparse
import subprocess
from pathlib import Path
from collections import defaultdict, Counter

PROJECT_ROOT = Path(__file__).parent.parent
APPS_DIR = PROJECT_ROOT / "apps_generated"
ANALYSES_DIR = PROJECT_ROOT / "analyses" / "static"
BANDIT_DIR = ANALYSES_DIR / "bandit"


def run_bandit_on(app_dir, output_file):
    """Exécute Bandit en JSON sur un dossier code/ et sauvegarde le résultat."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "bandit",
        "-r", str(app_dir),
        "-f", "json",
        "-o", str(output_file),
        "--exit-zero",   # toujours exit 0 même si findings (sinon Python plante)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return {"ok": True, "stderr": result.stderr[:300] if result.stderr else ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except FileNotFoundError:
        return {"ok": False, "error": "bandit non installé. Faire : pip install bandit"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def parse_bandit_json(json_file):
    """Parse un rapport Bandit JSON et retourne la liste des findings + métriques."""
    if not json_file.exists():
        return [], {}

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [], {"parse_error": str(e)}

    findings = []
    for r in data.get("results", []):
        findings.append({
            "test_id": r.get("test_id", ""),
            "test_name": r.get("test_name", ""),
            "issue_text": r.get("issue_text", "")[:300],
            "severity": r.get("issue_severity", ""),
            "confidence": r.get("issue_confidence", ""),
            "cwe_id": (r.get("issue_cwe", {}) or {}).get("id", ""),
            "filename": r.get("filename", ""),
            "line_number": r.get("line_number", 0),
        })

    metrics_global = data.get("metrics", {}).get("_totals", {})
    metrics = {
        "loc": metrics_global.get("loc", 0),
        "nosec": metrics_global.get("nosec", 0),
        "skipped_tests": metrics_global.get("skipped_tests", 0),
        "sev_low": metrics_global.get("SEVERITY.LOW", 0),
        "sev_medium": metrics_global.get("SEVERITY.MEDIUM", 0),
        "sev_high": metrics_global.get("SEVERITY.HIGH", 0),
        "sev_undefined": metrics_global.get("SEVERITY.UNDEFINED", 0),
    }
    return findings, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str, default=None,
                        help="Un seul modèle (ex: claude_opus)")
    parser.add_argument("--skip-run", action="store_true",
                        help="Ne pas relancer Bandit, juste consolider les JSON existants")
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
            code_dir = scenario_dir / "code"
            if not code_dir.exists():
                continue
            # Vérifier qu'il y a au moins un .py
            py_files = list(code_dir.rglob("*.py"))
            if not py_files:
                print("[skip] " + model_dir.name + "/" + scenario_dir.name
                      + " : aucun .py")
                continue
            tasks.append((model_dir.name, scenario_dir.name, code_dir))

    print("=" * 70)
    print("ANALYSE BANDIT")
    print("=" * 70)
    print("Applications à analyser : " + str(len(tasks)))
    print("=" * 70)

    # Étape 1 : Exécution
    if not args.skip_run:
        for i, (model, scenario, code_dir) in enumerate(tasks, 1):
            output_file = BANDIT_DIR / model / (scenario + ".json")
            print("[" + str(i) + "/" + str(len(tasks)) + "] "
                  + model + "/" + scenario + " ... ", end="", flush=True)
            res = run_bandit_on(code_dir, output_file)
            if res["ok"]:
                print("OK")
            else:
                print("ECHEC : " + res.get("error", "?"))

    # Étape 2 : Consolidation
    print("\nConsolidation...")
    all_findings = []
    summary_rows = []

    for model, scenario, code_dir in tasks:
        json_file = BANDIT_DIR / model / (scenario + ".json")
        findings, metrics = parse_bandit_json(json_file)

        # Enrichir chaque finding avec model/scenario
        for f in findings:
            f["model"] = model
            f["scenario"] = scenario
            # Chemin relatif
            try:
                rel = Path(f["filename"]).relative_to(code_dir)
                f["filename_relative"] = str(rel)
            except ValueError:
                f["filename_relative"] = f["filename"]
            all_findings.append(f)

        # Comptage par sévérité
        sev_counter = Counter(f["severity"] for f in findings)
        # Comptage par test_id
        test_counter = Counter(f["test_id"] for f in findings)

        summary_rows.append({
            "model": model,
            "scenario": scenario,
            "loc": metrics.get("loc", 0),
            "n_findings": len(findings),
            "n_high": sev_counter.get("HIGH", 0),
            "n_medium": sev_counter.get("MEDIUM", 0),
            "n_low": sev_counter.get("LOW", 0),
            "density_per_kloc": round((len(findings) / metrics["loc"]) * 1000, 2)
                                if metrics.get("loc", 0) > 0 else 0,
            "top_issues": ";".join([t + "(" + str(c) + ")"
                                    for t, c in test_counter.most_common(3)]),
        })

    # Sauvegarder findings consolidés (CSV)
    findings_csv = ANALYSES_DIR / "bandit_consolidated.csv"
    if all_findings:
        with open(findings_csv, "w", encoding="utf-8", newline="") as f:
            fieldnames = ["model", "scenario", "test_id", "test_name",
                          "severity", "confidence", "cwe_id",
                          "filename_relative", "line_number", "issue_text"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for fd in all_findings:
                writer.writerow(fd)
        print("  -> " + str(findings_csv) + " (" + str(len(all_findings)) + " findings)")

    # Sauvegarder synthèse (CSV)
    summary_csv = ANALYSES_DIR / "bandit_summary.csv"
    with open(summary_csv, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["model", "scenario", "loc", "n_findings", "n_high", "n_medium", "n_low",
                      "density_per_kloc", "top_issues"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)
    print("  -> " + str(summary_csv))

    # Synthèse lisible
    summary_txt = ANALYSES_DIR / "bandit_summary.txt"
    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("SYNTHESE BANDIT\n")
        f.write("=" * 80 + "\n\n")

        # Tableau par génération
        f.write(f"{'Modèle/Scénario':<45} {'LOC':>6} {'Total':>6} {'HIGH':>5} {'MED':>4} {'LOW':>4} {'/KLOC':>7}\n")
        f.write("-" * 80 + "\n")
        for r in summary_rows:
            label = r["model"] + "/" + r["scenario"]
            f.write(f"{label:<45} {r['loc']:>6} {r['n_findings']:>6} "
                    f"{r['n_high']:>5} {r['n_medium']:>4} {r['n_low']:>4} {r['density_per_kloc']:>7}\n")

        # Totaux par modèle
        f.write("\n" + "=" * 80 + "\n")
        f.write("AGREGATION PAR MODELE\n")
        f.write("=" * 80 + "\n\n")
        by_model = defaultdict(lambda: {"loc": 0, "n_findings": 0,
                                          "n_high": 0, "n_medium": 0, "n_low": 0})
        for r in summary_rows:
            m = by_model[r["model"]]
            m["loc"] += r["loc"]
            m["n_findings"] += r["n_findings"]
            m["n_high"] += r["n_high"]
            m["n_medium"] += r["n_medium"]
            m["n_low"] += r["n_low"]

        f.write(f"{'Modèle':<20} {'LOC tot':>8} {'Findings':>10} {'HIGH':>6} {'MED':>5} {'LOW':>5} {'/KLOC':>7}\n")
        f.write("-" * 70 + "\n")
        for model, m in sorted(by_model.items()):
            density = round((m["n_findings"] / m["loc"]) * 1000, 2) if m["loc"] > 0 else 0
            f.write(f"{model:<20} {m['loc']:>8} {m['n_findings']:>10} "
                    f"{m['n_high']:>6} {m['n_medium']:>5} {m['n_low']:>5} {density:>7}\n")

        # Top des règles violées
        f.write("\n" + "=" * 80 + "\n")
        f.write("TOP 10 DES REGLES BANDIT LES PLUS VIOLEES\n")
        f.write("=" * 80 + "\n\n")
        rule_counter = Counter(fd["test_id"] + " " + fd["test_name"] for fd in all_findings)
        for rule, count in rule_counter.most_common(10):
            f.write(f"  {count:>4}× {rule}\n")

        # Top CWE
        f.write("\n" + "=" * 80 + "\n")
        f.write("TOP CWE\n")
        f.write("=" * 80 + "\n\n")
        cwe_counter = Counter(fd["cwe_id"] for fd in all_findings if fd["cwe_id"])
        for cwe, count in cwe_counter.most_common(10):
            f.write(f"  {count:>4}× CWE-{cwe}\n")

    print("  -> " + str(summary_txt))

    # Affichage console final
    print("\n" + "=" * 70)
    print("RESUME RAPIDE")
    print("=" * 70)
    print("Total findings : " + str(len(all_findings)))
    sev_total = Counter(fd["severity"] for fd in all_findings)
    print("  HIGH   : " + str(sev_total.get("HIGH", 0)))
    print("  MEDIUM : " + str(sev_total.get("MEDIUM", 0)))
    print("  LOW    : " + str(sev_total.get("LOW", 0)))

    by_model_count = Counter(fd["model"] for fd in all_findings)
    print("\nPar modèle :")
    for model in sorted(set(t[0] for t in tasks)):
        print("  " + model + " : " + str(by_model_count.get(model, 0)) + " findings")


if __name__ == "__main__":
    main()
