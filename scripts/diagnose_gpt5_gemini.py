"""
diagnose_gpt5_gemini.py
-----------------------
Diagnostic ciblé pour résoudre les deux modèles qui échouent :
- GPT-5 : tester avec max_tokens élevé et reasoning minimal
- Gemini : tester plusieurs identifiants pour trouver celui qui marche
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("ERREUR : OPENROUTER_API_KEY introuvable")
    sys.exit(1)

URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://localhost/projet-cyber",
    "X-Title": "Projet Cyber - Atelier 2",
}


def call(payload, label):
    print(f"\n--- {label} ---")
    try:
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=120)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}")
            print(f"  Body: {r.text[:300]}")
            return False

        data = r.json()
        msg = data["choices"][0]["message"]
        finish = data["choices"][0].get("finish_reason")
        usage = data.get("usage", {})

        content = msg.get("content")
        print(f"  finish_reason : {finish}")
        print(f"  tokens : {usage.get('prompt_tokens')} in / "
              f"{usage.get('completion_tokens')} out "
              f"(reasoning_tokens={usage.get('completion_tokens_details', {}).get('reasoning_tokens', '?')})")
        print(f"  content type : {type(content).__name__}")
        if content:
            preview = str(content)[:80].replace('\n', ' ')
            print(f"  content : '{preview}'")
            return True
        else:
            print(f"  content VIDE")
            return False
    except Exception as e:
        print(f"  Exception : {e}")
        return False


# ============================================================
# GPT-5 : 3 tentatives avec différents paramètres
# ============================================================
print("=" * 70)
print("DIAGNOSTIC GPT-5")
print("=" * 70)

base_msg = [{"role": "user", "content": "Réponds juste avec le mot 'OK'."}]

# Tentative 1 : max_tokens très élevé (laisse de la place pour le reasoning)
call({
    "model": "openai/gpt-5",
    "messages": base_msg,
    "max_tokens": 2000,
    "temperature": 0,
}, "GPT-5 / max_tokens=2000")

# Tentative 2 : reasoning effort minimal
call({
    "model": "openai/gpt-5",
    "messages": base_msg,
    "max_tokens": 100,
    "temperature": 0,
    "reasoning": {"effort": "minimal"},
}, "GPT-5 / reasoning=minimal / max_tokens=100")

# Tentative 3 : GPT-5 mini (plus économique pour tests)
call({
    "model": "openai/gpt-5-mini",
    "messages": base_msg,
    "max_tokens": 2000,
    "temperature": 0,
}, "GPT-5-mini / max_tokens=2000")

# ============================================================
# GEMINI : plusieurs identifiants à essayer
# ============================================================
print("\n" + "=" * 70)
print("DIAGNOSTIC GEMINI")
print("=" * 70)

gemini_candidates = [
    "google/gemini-3-pro-preview",
    "google/gemini-3.1-pro-preview",
    "google/gemini-3-flash-preview",
    "google/gemini-3.1-flash-preview",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
]

for model_id in gemini_candidates:
    call({
        "model": model_id,
        "messages": base_msg,
        "max_tokens": 50,
        "temperature": 0,
    }, model_id)

print("\n" + "=" * 70)
print("Notez quels modèles fonctionnent ci-dessus.")
print("On utilisera celui qui marche dans le script principal.")
print("=" * 70)
