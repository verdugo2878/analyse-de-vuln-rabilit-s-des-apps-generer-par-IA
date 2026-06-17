import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from app import app
    try:
        from app import db
        with app.app_context():
            db.create_all()
    except (ImportError, AttributeError):
        pass
    app.run(host='127.0.0.1', port=5117, debug=False, use_reloader=False)
except ImportError as e:
    print("IMPORT_ERROR:" + str(e))
    sys.exit(1)
except Exception as e:
    print("RUN_ERROR:" + str(e))
    sys.exit(1)
