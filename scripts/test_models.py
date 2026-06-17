"""
test_models.py
--------------
Vérifie que la clé OpenRouter fonctionne et que les 6 modèles
sélectionnés répondent correctement avant de lancer la génération réelle.

Version 2 : gestion robuste des réponses (GPT-5 reasoning, content vide).

Usage:
    python test_models.py
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    print("ERREUR : variable OPENROUTER_API_KEY introuvable dans .env")
    sys.exit(1)

# Identifiants vérifiés sur openrouter.ai en mai 2026
MODELS = {
    "claude_opus":   "anthropic/claude-opus-4.7",
    "gpt5":          "openai/gpt-5",
    "gemini3":       "google/gemini-3-pro-preview",   # corrigé : ajout -preview
    "deepseek_v32":  "deepseek/deepseek-v3.2",
    "qwen3_coder":   "qwen/qwen3-coder",
    "llama_33":      "meta-llama/llama-3.3-70b-instruct",
}

URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://localhost/projet-cyber",
    "X-Title": "Projet Cyber - Atelier 2",
}


def extract_content(data):
    """
    Extrait le texte de réponse en gérant les cas particuliers
    (GPT-5 reasoning, Gemini avec champs alternatifs, etc.).
    Retourne (texte, source).
    """
    try:
        msg = data["choices"][0]["message"]
    except (KeyError, IndexError):
        return ("", "no_message")

    # Cas 1 : champ content standard
    content = msg.get("content")
    if content and isinstance(content, str) and content.strip():
        return (content.strip(), "content")

    # Cas 2 : content est une liste de blocs (format multimodal)
    if isinstance(content, list):
        texts = [b.get("text", "") for b in content if isinstance(b, dict)]
        joined = " ".join(t for t in texts if t).strip()
        if joined:
            return (joined, "content_blocks")

    # Cas 3 : reasoning seul (GPT-5 thinking)
    reasoning = msg.get("reasoning") or msg.get("reasoning_content")
    if reasoning and str(reasoning).strip():
        return (str(reasoning).strip()[:100], "reasoning")

    finish = data["choices"][0].get("finish_reason", "?")
    return ("", "empty (finish_reason=" + str(finish) + ")")


def test_model(label, model_id):
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": "Réponds juste avec le mot 'OK'."}
        ],
        "max_tokens": 50,
        "temperature": 0,
    }

    start = time.time()
    try:
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=90)
        elapsed = time.time() - start

        if r.status_code == 200:
            data = r.json()
            content, source = extract_content(data)
            usage = data.get("usage", {})
            return {
                "ok": bool(content),
                "label": label,
                "model_id": model_id,
                "response": content if content else "(vide)",
                "source": source,
                "elapsed": elapsed,
                "tokens_in": usage.get("prompt_tokens", "?"),
                "tokens_out": usage.get("completion_tokens", "?"),
                "raw": data,
            }
        else:
            return {
                "ok": False,
                "label": label,
                "model_id": model_id,
                "error": "HTTP " + str(r.status_code) + ": " + r.text[:300],
            }
    except Exception as e:
        return {
            "ok": False,
            "label": label,
            "model_id": model_id,
            "error": "Exception: " + type(e).__name__ + ": " + str(e),
        }


def main():
    print("=" * 70)
    print("Test de connexion aux 6 modèles OpenRouter (v2)")
    print("=" * 70)

    results = []
    for label, model_id in MODELS.items():
        print("\n[Test] " + label + " (" + model_id + ")...")
        res = test_model(label, model_id)
        results.append(res)

        if res["ok"]:
            print("  OK - Réponse: '" + res["response"][:50] + "' "
                  "[source=" + res["source"] + "] "
                  "(" + str(round(res["elapsed"], 1)) + "s, "
                  + str(res["tokens_in"]) + " in / "
                  + str(res["tokens_out"]) + " out)")
        else:
            if "error" in res:
                print("  ECHEC - " + res["error"])
            else:
                print("  REPONSE VIDE - source=" + str(res.get("source")) + " "
                      "(" + str(round(res.get("elapsed", 0), 1)) + "s, "
                      + str(res.get("tokens_in")) + " in / "
                      + str(res.get("tokens_out")) + " out)")
                if "raw" in res:
                    msg = res["raw"].get("choices", [{}])[0].get("message", {})
                    print("    Champs présents dans message : " + str(list(msg.keys())))
                    finish = res["raw"].get("choices", [{}])[0].get("finish_reason")
                    print("    finish_reason : " + str(finish))

    print("\n" + "=" * 70)
    print("Synthèse")
    print("=" * 70)
    success = sum(1 for r in results if r["ok"])
    print("Modèles fonctionnels : " + str(success) + "/" + str(len(MODELS)))

    if success < len(MODELS):
        print("\nPour les modèles en échec :")
        print("  - Vérifiez l'identifiant exact sur https://openrouter.ai/models")
        print("  - Pour les réponses vides, regardez les champs présents ci-dessus")
        print("  - Modifiez le dictionnaire MODELS en haut puis relancez")
    else:
        print("\nTout fonctionne. Vous pouvez passer à la génération réelle.")


if __name__ == "__main__":
    main()
