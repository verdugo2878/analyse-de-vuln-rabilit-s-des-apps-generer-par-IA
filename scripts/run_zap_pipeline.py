"""
run_zap_pipeline.py
-------------------
Pipeline automatisé OWASP ZAP sur les apps déployables.

Pour chaque app dans deployable_apps.json (statut ok=True) :
1. Démarre l'app Flask en arrière-plan
2. Lance ZAP en mode daemon (CLI, sans GUI)
3. Lance Spider + Active Scan
4. Exporte le rapport HTML
5. Tue l'app

Sortie : analyses/dynamic/zap/<model>/<scenario>.html

Prérequis :
- ZAP installé dans C:\\Program Files\\ZAP\\Zed Attack Proxy\\
- deployable_apps.json existant (généré par test_apps_deployable.py)

Usage :
    python scripts/run_zap_pipeline.py
    python scripts/run_zap_pipeline.py --only claude_opus/S3_boutique
"""

import os
import sys
import json
import time
import argparse
import subprocess
import urllib.request
import urllib.error
import socket
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
APPS_DIR = PROJECT_ROOT / "apps_generated"
ANALYSES_DIR = PROJECT_ROOT / "analyses" / "dynamic"
ZAP_REPORTS_DIR = ANALYSES_DIR / "zap"
DEPLOYABLE_JSON = ANALYSES_DIR / "deployable_apps.json"

ZAP_BAT = Path("C:/Program Files/ZAP/Zed Attack Proxy/zap.bat")
ZAP_PORT = 8090  # Port du proxy ZAP en mode daemon

# Délais
APP_STARTUP_TIMEOUT = 30
ZAP_STARTUP_TIMEOUT = 60
SPIDER_TIMEOUT = 180   # 3 min max pour Spider
ACTIVE_SCAN_TIMEOUT = 600  # 10 min max pour Active Scan


def is_port_free(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
        return True
    except OSError:
        return False


def wait_for_url(url, timeout):
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except urllib.error.HTTPError:
            return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(1)
    return False


def zap_api(endpoint, **params):
    """Appelle l'API ZAP."""
    base = "http://localhost:" + str(ZAP_PORT) + "/JSON/"
    qs = "&".join([k + "=" + str(v) for k, v in params.items()])
    url = base + endpoint + "/?" + qs if qs else base + endpoint + "/"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def zap_other(endpoint, **params):
    """Appelle l'API ZAP pour les exports (HTML, XML)."""
    base = "http://localhost:" + str(ZAP_PORT) + "/OTHER/"
    qs = "&".join([k + "=" + str(v) for k, v in params.items()])
    url = base + endpoint + "/?" + qs if qs else base + endpoint + "/"
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            return resp.read()
    except Exception as e:
        return None


def start_zap_daemon():
    """Démarre ZAP en mode daemon (sans GUI)."""
    print("Démarrage de ZAP en mode daemon...")
    if not ZAP_BAT.exists():
        return None, "zap.bat introuvable: " + str(ZAP_BAT)

    # ZAP doit être lancé depuis son dossier
    zap_dir = ZAP_BAT.parent
    cmd = [str(ZAP_BAT), "-daemon", "-port", str(ZAP_PORT),
           "-config", "api.disablekey=true",
           "-config", "api.addrs.addr.name=.*",
           "-config", "api.addrs.addr.regex=true"]

    proc = subprocess.Popen(
        cmd,
        cwd=str(zap_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )

    # Attendre que ZAP réponde
    print("  Attente du démarrage de ZAP (peut prendre 30-60 sec)...")
    if wait_for_url("http://localhost:" + str(ZAP_PORT), ZAP_STARTUP_TIMEOUT):
        print("  ZAP démarré sur le port " + str(ZAP_PORT))
        return proc, None
    else:
        proc.terminate()
        return None, "ZAP n'a pas démarré dans " + str(ZAP_STARTUP_TIMEOUT) + "s"


def stop_zap(proc):
    """Arrête ZAP proprement via son API puis tue le processus."""
    print("Arrêt de ZAP...")
    try:
        zap_api("core/action/shutdown")
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def start_app(code_dir, port):
    """Démarre une app Flask en arrière-plan."""
    venv_python = code_dir / "venv_zap" / "Scripts" / "python.exe"
    launcher = code_dir / "run_zap.py"

    if not venv_python.exists() or not launcher.exists():
        return None, "venv_zap ou run_zap.py manquant"

    proc = subprocess.Popen(
        [str(venv_python), str(launcher)],
        cwd=str(code_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )

    url = "http://127.0.0.1:" + str(port)
    if wait_for_url(url, APP_STARTUP_TIMEOUT):
        return proc, None
    else:
        try:
            proc.terminate()
        except Exception:
            pass
        return None, "app n'a pas démarré dans " + str(APP_STARTUP_TIMEOUT) + "s"


def stop_app(proc):
    """Arrête l'app Flask."""
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def scan_app(target_url, label):
    """Scanne une app via l'API ZAP : Spider + Active Scan."""
    print("  [Spider] Démarrage...")
    res = zap_api("spider/action/scan", url=target_url, recurse="true")
    if "scan" not in res:
        return False, "Spider n'a pas démarré: " + str(res)

    spider_id = res["scan"]
    start = time.time()
    while True:
        if time.time() - start > SPIDER_TIMEOUT:
            print("  [Spider] timeout, on stoppe")
            zap_api("spider/action/stop", scanId=spider_id)
            break
        status = zap_api("spider/view/status", scanId=spider_id)
        progress = status.get("status", "0")
        if progress == "100":
            print("  [Spider] terminé (100%)")
            break
        time.sleep(3)

    print("  [Active Scan] Démarrage...")
    res = zap_api("ascan/action/scan", url=target_url, recurse="true",
                  inScopeOnly="false")
    if "scan" not in res:
        return False, "Active Scan n'a pas démarré: " + str(res)

    scan_id = res["scan"]
    start = time.time()
    while True:
        elapsed = int(time.time() - start)
        if elapsed > ACTIVE_SCAN_TIMEOUT:
            print("  [Active Scan] timeout, on stoppe")
            zap_api("ascan/action/stop", scanId=scan_id)
            break
        status = zap_api("ascan/view/status", scanId=scan_id)
        progress = status.get("status", "0")
        if progress == "100":
            print("  [Active Scan] terminé (100%) en " + str(elapsed) + "s")
            break
        if elapsed % 30 == 0:
            print("  [Active Scan] progress=" + str(progress) + "% (" + str(elapsed) + "s)")
        time.sleep(5)

    return True, "OK"


def export_report(label, output_html, output_json):
    """Exporte les rapports HTML et JSON de ZAP."""
    print("  Export HTML...")
    html = zap_other("htmlreport")
    if html:
        output_html.parent.mkdir(parents=True, exist_ok=True)
        with open(output_html, "wb") as f:
            f.write(html)
        print("    -> " + str(output_html))

    print("  Export JSON...")
    res = zap_api("alert/view/alerts", baseurl="")
    if "alerts" in res:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print("    -> " + str(output_json) + " (" + str(len(res["alerts"])) + " alertes)")


def reset_zap():
    """Reset ZAP entre les apps pour repartir propre."""
    zap_api("core/action/newSession", overwrite="true")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str, default=None,
                        help="Format model/scenario, ex: claude_opus/S3_boutique")
    args = parser.parse_args()

    # Charger les apps déployables
    if not DEPLOYABLE_JSON.exists():
        print("ERREUR : " + str(DEPLOYABLE_JSON) + " introuvable")
        print("Lancer d'abord : python scripts/test_apps_deployable.py")
        sys.exit(1)

    with open(DEPLOYABLE_JSON, "r", encoding="utf-8") as f:
        all_apps = json.load(f)

    deployable = [a for a in all_apps if a.get("ok")]
    if args.only:
        deployable = [a for a in deployable if a["label"] == args.only]

    if not deployable:
        print("Aucune app déployable trouvée")
        sys.exit(0)

    print("=" * 70)
    print("PIPELINE ZAP AUTOMATISE")
    print("=" * 70)
    print("Apps à scanner : " + str(len(deployable)))
    for a in deployable:
        print("  - " + a["label"] + " sur " + a["url"])
    print("=" * 70)

    # Démarrer ZAP une seule fois
    zap_proc, err = start_zap_daemon()
    if err:
        print("ECHEC démarrage ZAP : " + err)
        sys.exit(1)

    try:
        for i, app in enumerate(deployable, 1):
            label = app["label"]
            model, scenario = label.split("/")
            url = app["url"]
            port = app["port"]

            print("\n" + "=" * 70)
            print("[" + str(i) + "/" + str(len(deployable)) + "] " + label)
            print("URL: " + url)
            print("=" * 70)

            # Nouvelle session ZAP propre
            reset_zap()

            # Démarrer l'app
            code_dir = APPS_DIR / model / scenario / "code"
            print("Démarrage de l'app...")
            app_proc, err = start_app(code_dir, port)
            if err:
                print("  ECHEC : " + err)
                continue
            print("  App répond sur " + url)

            try:
                # Scanner avec ZAP
                ok, msg = scan_app(url, label)
                if not ok:
                    print("  ECHEC scan : " + msg)
                    continue

                # Exporter les rapports
                output_html = ZAP_REPORTS_DIR / model / (scenario + ".html")
                output_json = ZAP_REPORTS_DIR / model / (scenario + "_alerts.json")
                export_report(label, output_html, output_json)
            finally:
                stop_app(app_proc)
                # Petit délai pour libérer le port
                time.sleep(2)

    finally:
        stop_zap(zap_proc)

    print("\n" + "=" * 70)
    print("PIPELINE TERMINE")
    print("=" * 70)
    print("Rapports dans : " + str(ZAP_REPORTS_DIR))


if __name__ == "__main__":
    main()
