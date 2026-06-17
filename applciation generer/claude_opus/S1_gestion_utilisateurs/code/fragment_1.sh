# 1. Créer le dossier projet et les sous-dossiers
mkdir -p user_management/templates user_management/static/uploads
cd user_management

# 2. Copier tous les fichiers ci-dessus

# 3. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Lancer l'application
python app.py
