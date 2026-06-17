"""
generate_apps.py
----------------
Script principal de génération des 24 applications web (6 LLMs × 4 scénarios).

Fonctionnalités :
- Charge les 4 prompts depuis prompts/prompts.json
- Itère sur les 6 modèles configurés
- Sauvegarde réponse brute (response.md) + métadonnées (metadata.json)
- Idempotent : ne regénère pas ce qui existe déjà
- Estimation du coût cumulé
- Reprise sur erreur

Usage :
    python scripts/generate_apps.py              # Génère tout ce qui manque
    python scripts/generate_apps.py --dry-run    # Simule sans appeler l'API
    python scripts/generate_apps.py --only claude_opus    # Un seul modèle
    python scripts/generate_apps.py --only claude_opus --scenario S1_gestion_utilisateurs

Prérequis :
    - Fichier .env avec OPENROUTER_API_KEY
    - Fichier prompts/prompts.json
    - Dossier apps_generated/ (créé automatiquement si absent)
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
import requests
from dotenv import load_dotenv

# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("ERREUR : OPENROUTER_API_KEY introuvable dans .env")
    sys.exit(1)

# Racine du projet (dossier parent du dossier scripts/)
PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_FILE = PROJECT_ROOT / "prompts" / "prompts.json"
APPS_DIR = PROJECT_ROOT / "apps_generated"
LOG_FILE = PROJECT_ROOT / "apps_generated" / "generation_log.jsonl"

# Configuration des 6 modèles
# 'reasoning_minimal' = forcer effort=minimal pour les modèles reasoning
# 'max_tokens' = budget tokens output
MODELS = {
    "claude_opus": {
        "id": "anthropic/claude-opus-4.7",
        "max_tokens": 16000,
        "reasoning_minimal": False,
        "price_in_per_M": 5.0,
        "price_out_per_M": 25.0,
    },
    "gpt5": {
        "id": "openai/gpt-5",
        "max_tokens": 16000,
        "reasoning_minimal": True,   # économise les tokens reasoning
        "price_in_per_M": 1.25,
        "price_out_per_M": 10.0,
    },
    "gemini3": {
        "id": "google/gemini-3.1-pro-preview",
        "max_tokens": 16000,
        "reasoning_minimal": True,   # idem, c'est un modèle reasoning
        "price_in_per_M": 2.0,
        "price_out_per_M": 12.0,
    },
    "deepseek_v32": {
        "id": "deepseek/deepseek-v3.2",
        "max_tokens": 16000,
        "reasoning_minimal": False,
        "price_in_per_M": 0.27,
        "price_out_per_M": 1.10,
    },
    "qwen3_coder": {
        "id": "qwen/qwen3-coder",
        "max_tokens": 16000,
        "reasoning_minimal": False,
        "price_in_per_M": 1.0,
        "price_out_per_M": 5.0,
    },
    "llama_33": {
        "id": "meta-llama/llama-3.3-70b-instruct",
        "max_tokens": 16000,
        "reasoning_minimal": False,
        "price_in_per_M": 0.13,
        "price_out_per_M": 0.39,
    },
}

URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": "Bearer " + API_KEY,
    "Content-Type": "application/json",
    "HTTP-Referer": "https://localhost/projet-cyber",
    "X-Title": "Projet Cyber - Atelier 2",
}

DELAY_BETWEEN_REQUESTS = 2  # secondes


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def load_prompts():
    """Charge les prompts depuis le fichier JSON."""
    if not PROMPTS_FILE.exists():
        print("ERREUR : fichier introuvable : " + str(PROMPTS_FILE))
        print("Créez d'abord prompts/prompts.json")
        sys.exit(1)
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def output_dir(model_label, scenario_label):
    """Retourne le chemin où sauvegarder cette génération."""
    return APPS_DIR / model_label / scenario_label


def already_generated(model_label, scenario_label):
    """Vérifie si la génération existe déjà (et est valide)."""
    d = output_dir(model_label, scenario_label)
    response_file = d / "response.md"
    metadata_file = d / "metadata.json"
    if response_file.exists() and metadata_file.exists():
        # Vérifier que la réponse n'est pas vide
        if response_file.stat().st_size > 100:
            return True
    return False


def extract_content(data):
    """Extrait le texte de réponse en gérant les cas particuliers."""
    try:
        msg = data["choices"][0]["message"]
    except (KeyError, IndexError):
        return ""

    content = msg.get("content")
    if content and isinstance(content, str) and content.strip():
        return content

    if isinstance(content, list):
        texts = [b.get("text", "") for b in content if isinstance(b, dict)]
        return "\n".join(t for t in texts if t)

    return ""


def estimate_cost(model_config, tokens_in, tokens_out):
    """Estime le coût en USD d'une génération."""
    cost = (tokens_in / 1_000_000) * model_config["price_in_per_M"] \
         + (tokens_out / 1_000_000) * model_config["price_out_per_M"]
    return cost


def log_generation(entry):
    """Ajoute une entrée au fichier de log JSONL."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================
# GÉNÉRATION
# ============================================================

def generate_one(model_label, model_config, scenario_label, prompt_text, dry_run=False):
    """
    Génère une seule application et la sauvegarde.
    Retourne un dict de résultat.
    """
    out_dir = output_dir(model_label, scenario_label)

    if dry_run:
        print("  [DRY-RUN] Simulerait : " + model_label + " / " + scenario_label)
        return {"ok": True, "skipped": True, "cost": 0}

    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "model": model_config["id"],
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": model_config["max_tokens"],
        "temperature": 0.7,
    }
    if model_config.get("reasoning_minimal"):
        payload["reasoning"] = {"effort": "minimal"}

    start = time.time()
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=600)
        elapsed = time.time() - start

        if r.status_code != 200:
            error = "HTTP " + str(r.status_code) + " : " + r.text[:500]
            metadata = {
                "ok": False,
                "error": error,
                "model_label": model_label,
                "model_id": model_config["id"],
                "scenario": scenario_label,
                "timestamp_utc": timestamp,
                "elapsed_seconds": elapsed,
            }
            with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            log_generation(metadata)
            return {"ok": False, "error": error, "cost": 0}

        data = r.json()
        content = extract_content(data)

        if not content or len(content) < 200:
            finish = data.get("choices", [{}])[0].get("finish_reason", "?")
            error = "Réponse trop courte ou vide (finish_reason=" + str(finish) + ")"
            metadata = {
                "ok": False,
                "error": error,
                "model_label": model_label,
                "model_id": model_config["id"],
                "scenario": scenario_label,
                "timestamp_utc": timestamp,
                "elapsed_seconds": elapsed,
                "raw_response": data,
            }
            with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            log_generation({k: v for k, v in metadata.items() if k != "raw_response"})
            return {"ok": False, "error": error, "cost": 0}

        # Succès
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        reasoning_tokens = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        cost = estimate_cost(model_config, tokens_in, tokens_out)
        finish = data.get("choices", [{}])[0].get("finish_reason", "?")

        # Sauvegarder la réponse brute
        with open(out_dir / "response.md", "w", encoding="utf-8") as f:
            f.write(content)

        # Sauvegarder les métadonnées
        metadata = {
            "ok": True,
            "model_label": model_label,
            "model_id": model_config["id"],
            "scenario": scenario_label,
            "timestamp_utc": timestamp,
            "elapsed_seconds": round(elapsed, 2),
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "reasoning_tokens": reasoning_tokens,
            "finish_reason": finish,
            "cost_usd_estimated": round(cost, 6),
            "temperature": 0.7,
            "max_tokens_param": model_config["max_tokens"],
            "reasoning_minimal": model_config.get("reasoning_minimal", False),
            "response_length_chars": len(content),
        }
        with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        log_generation(metadata)

        return {
            "ok": True,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost": cost,
            "elapsed": elapsed,
            "finish_reason": finish,
        }

    except Exception as e:
        error = "Exception : " + type(e).__name__ + " : " + str(e)
        return {"ok": False, "error": error, "cost": 0}


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Simule sans appeler l'API")
    parser.add_argument("--only", type=str, default=None,
                        help="Ne génère que pour ce modèle (ex: claude_opus)")
    parser.add_argument("--scenario", type=str, default=None,
                        help="Ne génère que pour ce scénario (ex: S1_gestion_utilisateurs)")
    parser.add_argument("--force", action="store_true",
                        help="Force la regénération même si déjà existant")
    args = parser.parse_args()

    prompts_data = load_prompts()
    prompts = prompts_data["prompts"]

    # Filtrage
    models_to_run = MODELS
    if args.only:
        if args.only not in MODELS:
            print("Modèle inconnu : " + args.only)
            print("Modèles disponibles : " + ", ".join(MODELS.keys()))
            sys.exit(1)
        models_to_run = {args.only: MODELS[args.only]}

    scenarios_to_run = prompts
    if args.scenario:
        if args.scenario not in prompts:
            print("Scénario inconnu : " + args.scenario)
            print("Scénarios disponibles : " + ", ".join(prompts.keys()))
            sys.exit(1)
        scenarios_to_run = {args.scenario: prompts[args.scenario]}

    # Plan d'exécution
    tasks = []
    for model_label in models_to_run:
        for scenario_label in scenarios_to_run:
            tasks.append((model_label, scenario_label))

    total = len(tasks)
    print("=" * 70)
    print("GÉNÉRATION DES APPLICATIONS")
    print("=" * 70)
    print("Modèles  : " + str(list(models_to_run.keys())))
    print("Scénarios: " + str(list(scenarios_to_run.keys())))
    print("Total    : " + str(total) + " génération(s)")
    if args.dry_run:
        print("Mode     : DRY-RUN (aucun appel API)")
    print("=" * 70)

    total_cost = 0
    n_success = 0
    n_skipped = 0
    n_error = 0
    errors = []

    for i, (model_label, scenario_label) in enumerate(tasks, 1):
        print("\n[" + str(i) + "/" + str(total) + "] " + model_label + " / " + scenario_label)

        if not args.force and already_generated(model_label, scenario_label):
            print("  Déjà généré, on saute (utiliser --force pour regénérer)")
            n_skipped += 1
            continue

        model_config = models_to_run[model_label]
        prompt_text = scenarios_to_run[scenario_label]

        result = generate_one(model_label, model_config, scenario_label, prompt_text,
                              dry_run=args.dry_run)

        if result["ok"] and not result.get("skipped"):
            cost = result["cost"]
            total_cost += cost
            n_success += 1
            print("  OK - " + str(result["tokens_in"]) + " in / "
                  + str(result["tokens_out"]) + " out, "
                  + str(round(result["elapsed"], 1)) + "s, "
                  + "coût=$" + str(round(cost, 4))
                  + " (cumul=$" + str(round(total_cost, 4)) + ")")
        elif result.get("skipped"):
            n_skipped += 1
        else:
            n_error += 1
            errors.append((model_label, scenario_label, result.get("error", "?")))
            print("  ECHEC - " + str(result.get("error", "?"))[:200])

        # Délai entre requêtes (sauf dernière)
        if i < total and not args.dry_run:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Synthèse
    print("\n" + "=" * 70)
    print("SYNTHÈSE")
    print("=" * 70)
    print("Succès  : " + str(n_success))
    print("Sautés  : " + str(n_skipped))
    print("Échecs  : " + str(n_error))
    print("Coût total estimé : $" + str(round(total_cost, 4)))

    if errors:
        print("\nDétail des échecs :")
        for model_label, scenario_label, error in errors:
            print("  - " + model_label + " / " + scenario_label + " : " + error[:150])
        print("\nPour relancer les échecs, supprimez les dossiers correspondants")
        print("dans apps_generated/ puis relancez le script.")


if __name__ == "__main__":
    main()
