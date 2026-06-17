# Auto-généré par test_apps_deployable.py
import sys
import os

# Ajouter le dossier courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Pattern 1 : import classique (Flask)
    from app import app
    # Tenter d'initialiser la base si une fonction init_db existe
    try:
        from app import init_db
        init_db()
    except (ImportError, AttributeError):
        pass
    # Ou create_all via SQLAlchemy directement
    try:
        from app import db
        with app.app_context():
            db.create_all()
    except (ImportError, AttributeError, Exception):
        pass
    app.run(host='127.0.0.1', port=5106, debug=False, use_reloader=False)
except ImportError as e:
    print("IMPORT_ERROR:" + str(e))
    sys.exit(1)
except Exception as e:
    print("RUN_ERROR:" + str(e))
    sys.exit(1)
