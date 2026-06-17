# Application Web de Gestion d'Utilisateurs avec Flask

Voici une application complète et prête à exécuter avec toutes les fonctionnalités demandées.

## Structure du projet

```
user_management/
├── app.py
├── requirements.txt
├── static/
│   └── uploads/
└── templates/
    ├── base.html
    ├── index.html
    ├── register.html
    ├── login.html
    ├── profile.html
    ├── edit_profile.html
    ├── admin.html
    └── dashboard.html
```

## 1. `requirements.txt`

```txt
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Werkzeug==3.0.1
Pillow==10.1.0
```

## 2. `app.py`

```python
import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

# ============ CONFIGURATION ============
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-in-production-please'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 Mo max
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'

# ============ MODÈLES ============
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text, default='')
    photo = db.Column(db.String(255), default='default.png')
    role = db.Column(db.String(20), default='user')  # 'user' ou 'admin'
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        # Flask-Login utilise cette propriété pour bloquer les comptes désactivés
        return self.is_active_account

# ============ HELPERS ============
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated

# ============ ROUTES ============
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not name or not email or not password:
            flash('Tous les champs sont obligatoires.', 'danger')
            return redirect(url_for('register'))

        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('register'))

        user = User(name=name, email=email)
        user.set_password(password)

        # Premier utilisateur créé = admin
        if User.query.count() == 0:
            user.role = 'admin'

        db.session.add(user)
        db.session.commit()
        flash('Inscription réussie ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active_account:
                flash('Votre compte a été désactivé. Contactez un administrateur.', 'danger')
                return redirect(url_for('login'))

            login_user(user)
            flash(f'Bienvenue, {user.name} !', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou mot de passe incorrect.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        bio = request.form.get('bio', '').strip()

        if not name or not email:
            flash('Le nom et l\'email sont obligatoires.', 'danger')
            return redirect(url_for('edit_profile'))

        # Vérifier si l'email est déjà pris par un autre utilisateur
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('edit_profile'))

        current_user.name = name
        current_user.email = email
        current_user.bio = bio

        # Gestion de la photo
        file = request.files.get('photo')
        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(f"user_{current_user.id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                current_user.photo = filename
            else:
                flash('Format d\'image non autorisé (png, jpg, jpeg, gif).', 'danger')
                return redirect(url_for('edit_profile'))

        # Changement de mot de passe optionnel
        new_password = request.form.get('new_password', '')
        if new_password:
            if len(new_password) < 6:
                flash('Le nouveau mot de passe doit contenir au moins 6 caractères.', 'danger')
                return redirect(url_for('edit_profile'))
            current_user.set_password(new_password)

        db.session.commit()
        flash('Profil mis à jour avec succès !', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=current_user)

# ============ ADMIN ============
@app.route('/admin')
@login_required
@admin_required
def admin():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin.html', users=users)

@app.route('/admin/toggle/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Vous ne pouvez pas désactiver votre propre compte.', 'warning')
        return redirect(url_for('admin'))

    user.is_active_account = not user.is_active_account
    db.session.commit()
    status = 'activé' if user.is_active_account else 'désactivé'
    flash(f'Compte de {user.name} {status}.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/role/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Vous ne pouvez pas modifier votre propre rôle.', 'warning')
        return redirect(url_for('admin'))

    new_role = request.form.get('role')
    if new_role in ['user', 'admin']:
        user.role = new_role
        db.session.commit()
        flash(f'Rôle de {user.name} changé en {new_role}.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'warning')
        return redirect(url_for('admin'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Utilisateur {user.name} supprimé.', 'success')
    return redirect(url_for('admin'))

# ============ ERREURS ============
@app.errorhandler(403)
def forbidden(e):
    return "<h1>403 - Accès interdit</h1><a href='/'>Retour</a>", 403

@app.errorhandler(404)
def not_found(e):
    return "<h1>404 - Page non trouvée</h1><a href='/'>Retour</a>", 404

# ============ INIT ============
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
```

## 3. `templates/base.html`

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Gestion Utilisateurs{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f4f6f9; }
        .profile-pic { width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 3px solid #0d6efd; }
        .avatar-small { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
        .navbar-brand { font-weight: bold; }
    </style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
    <div class="container">
        <a class="navbar-brand" href="{{ url_for('index') }}">🔐 UserApp</a>
        <div class="collapse navbar-collapse">
            <ul class="navbar-nav ms-auto">
                {% if current_user.is_authenticated %}
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a></li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('profile') }}">Mon Profil</a></li>
                    {% if current_user.role == 'admin' %}
                        <li class="nav-item"><a class="nav-link" href="{{ url_for('admin') }}">Admin</a></li>
                    {% endif %}
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Déconnexion</a></li>
                {% else %}
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Connexion</a></li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('register') }}">Inscription</a></li>
                {% endif %}
            </ul>
        </div>
    </div>
</nav>

<div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, msg in messages %}
            <div class="alert alert-{{ category }} alert-dismissible fade show">
                {{ msg }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        {% endfor %}
    {% endwith %}

    {% block content %}{% endblock %}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

## 4. `templates/index.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="text-center p-5 bg-white rounded shadow">
    <h1 class="display-4">Bienvenue sur UserApp</h1>
    <p class="lead">Plateforme de gestion d'utilisateurs complète.</p>
    {% if not current_user.is_authenticated %}
        <a href="{{ url_for('register') }}" class="btn btn-primary btn-lg">S'inscrire</a>
        <a href="{{ url_for('login') }}" class="btn btn-outline-primary btn-lg">Se connecter</a>
    {% else %}
        <a href="{{ url_for('dashboard') }}" class="btn btn-primary btn-lg">Mon Dashboard</a>
    {% endif %}
</div>
{% endblock %}
```

## 5. `templates/register.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card shadow">
            <div class="card-body">
                <h3 class="card-title text-center mb-4">Inscription</h3>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Nom</label>
                        <input type="text" name="name" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        <input type="email" name="email" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Mot de passe</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Confirmer le mot de passe</label>
                        <input type="password" name="confirm" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">S'inscrire</button>
                </form>
                <p class="text-center mt-3">
                    Déjà un compte ? <a href="{{ url_for('login') }}">Se connecter</a>
                </p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## 6. `templates/login.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow">
            <div class="card-body">
                <h3 class="card-title text-center mb-4">Connexion</h3>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        <input type="email" name="email" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Mot de passe</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Se connecter</button>
                </form>
                <p class="text-center mt-3">
                    Pas de compte ? <a href="{{ url_for('register') }}">S'inscrire</a>
                </p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## 7. `templates/dashboard.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="card shadow">
    <div class="card-body">
        <h2>Bonjour, {{ current_user.name }} 👋</h2>
        <p>Bienvenue sur votre tableau de bord.</p>
        <hr>
        <a href="{{ url_for('profile') }}" class="btn btn-primary">Voir mon profil</a>
        <a href="{{ url_for('edit_profile') }}" class="btn btn-outline-primary">Modifier mon profil</a>
        {% if current_user.role == 'admin' %}
            <a href="{{ url_for('admin') }}" class="btn btn-warning">Espace Admin</a>
        {% endif %}
    </div>
</div>
{% endblock %}
```

## 8. `templates/profile.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="card shadow">
    <div class="card-body text-center">
        {% if user.photo and user.photo != 'default.png' %}
            <img src="{{ url_for('static', filename='uploads/' + user.photo) }}" class="profile-pic mb-3">
        {% else %}
            <img src="https://via.placeholder.com/120?text=👤" class="profile-pic mb-3">
        {% endif %}
        <h3>{{ user.name }}</h3>
        <p class="text-muted">{{ user.email }}</p>
        <span class="badge bg-{{ 'danger' if user.role == 'admin' else 'secondary' }}">{{ user.role }}</span>
        <hr>
        <h5>Bio</h5>
        <p>{{ user.bio or 'Aucune biographie renseignée.' }}</p>
        <p class="text-muted small">Inscrit le {{ user.created_at.strftime('%d/%m/%Y') }}</p>
        <a href="{{ url_for('edit_profile') }}" class="btn btn-primary">Modifier mon profil</a>
    </div>
</div>
{% endblock %}
```

## 9. `templates/edit_profile.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-7">
        <div class="card shadow">
            <div class="card-body">
                <h3 class="mb-4">Modifier mon profil</h3>
                <form method="POST" enctype="multipart/form-data">
                    <div class="mb-3">
                        <label class="form-label">Nom</label>
                        <input type="text" name="name" class="form-control" value="{{ user.name }}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        <input type="email" name="email" class="form-control" value="{{ user.email }}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Bio</label>
                        <textarea name="bio" class="form-control" rows="4">{{ user.bio }}</textarea>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Photo de profil</label>
                        <input type="file" name="photo" class="form-control" accept="image/*">
                        {% if user.photo and user.photo != 'default.png' %}
                            <small>Photo actuelle : {{ user.photo }}</small>
                        {% endif %}
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Nouveau mot de passe (optionnel)</label>
                        <input type="password" name="new_password" class="form-control">
                    </div>
                    <button type="submit" class="btn btn-success">Enregistrer</button>
                    <a href="{{ url_for('profile') }}" class="btn btn-secondary">Annuler</a>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## 10. `templates/admin.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="card shadow">
    <div class="card-body">
        <h2>🛠️ Espace Administrateur</h2>
        <p class="text-muted">Total : {{ users|length }} utilisateur(s)</p>
        <div class="table-responsive">
            <table class="table table-hover align-middle">
                <thead class="table-dark">
                    <tr>
                        <th>ID</th>
                        <th>Photo</th>
                        <th>Nom</th>
                        <th>Email</th>
                        <th>Rôle</th>
                        <th>Statut</th>
                        <th>Inscrit le</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for u in users %}
                    <tr>
                        <td>{{ u.id }}</td>
                        <td>
                            {% if u.photo and u.photo != 'default.png' %}
                                <img src="{{ url_for('static', filename='uploads/' + u.photo) }}" class="avatar-small">
                            {% else %}
                                <span>👤</span>
                            {% endif %}
                        </td>
                        <td>{{ u.name }}</td>
                        <td>{{ u.email }}</td>
                        <td>
                            <form method="POST" action="{{ url_for('change_role', user_id=u.id) }}" class="d-flex">
                                <select name="role" class="form-select form-select-sm me-1" {% if u.id == current_user.id %}disabled{% endif %}>
                                    <option value="user" {% if u.role == 'user' %}selected{% endif %}>user</option>
                                    <option value="admin" {% if u.role == 'admin' %}selected{% endif %}>admin</option>
                                </select>
                                {% if u.id != current_user.id %}
                                <button class="btn btn-sm btn-outline-primary">OK</button>
                                {% endif %}
                            </form>
                        </td>
                        <td>
                            {% if u.is_active_account %}
                                <span class="badge bg-success">Actif</span>
                            {% else %}
                                <span class="badge bg-danger">Désactivé</span>
                            {% endif %}
                        </td>
                        <td>{{ u.created_at.strftime('%d/%m/%Y') }}</td>
                        <td>
                            {% if u.id != current_user.id %}
                                <form method="POST" action="{{ url_for('toggle_user', user_id=u.id) }}" class="d-inline">
                                    <button class="btn btn-sm btn-{{ 'warning' if u.is_active_account else 'success' }}">
                                        {{ 'Désactiver' if u.is_active_account else 'Activer' }}
                                    </button>
                                </form>
                                <form method="POST" action="{{ url_for('delete_user', user_id=u.id) }}" class="d-inline"
                                      onsubmit="return confirm('Supprimer définitivement cet utilisateur ?');">
                                    <button class="btn btn-sm btn-danger">Supprimer</button>
                                </form>
                            {% else %}
                                <em class="text-muted">Vous</em>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
```

## 🚀 Instructions de démarrage

```bash
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
```

Ouvrez ensuite **http://127.0.0.1:5000** dans votre navigateur.

## ✨ Fonctionnalités incluses

- ✅ **Inscription** avec validation (email unique, mot de passe ≥ 6 caractères)
- ✅ **Connexion / Déconnexion** sécurisée avec Flask-Login
- ✅ **Mot de passe hashé** avec Werkzeug (sécurisé)
- ✅ **Profil utilisateur** : nom, email, bio, photo de profil (upload)
- ✅ **Modification du profil** + changement de mot de passe
- ✅ **Espace admin** : liste de tous les utilisateurs, désactivation/activation, changement de rôle, suppression
- ✅ **Protection** : le premier utilisateur inscrit devient automatiquement **admin**
- ✅ **Comptes désactivés** : impossible de se connecter
- ✅ **Sécurité** : un admin ne peut pas se désactiver/supprimer lui-même
- ✅ **Interface Bootstrap 5** responsive et moderne

## 🔒 Pour la production

- Change `SECRET_KEY` par une valeur aléatoire (ex: `os.urandom(24).hex()`)
- Mets `debug=False`
- Utilise PostgreSQL à la place de SQLite
- Ajoute un CSRF (Flask-WTF) pour protéger les formulaires
- Utilise HTTPS + un serveur WSGI (gunicorn + nginx)