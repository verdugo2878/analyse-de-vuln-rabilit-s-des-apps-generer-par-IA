Voici une application web complète qui répond à vos besoins. Elle utilise **Flask**, **Flask-SQLAlchemy** (pour SQLite), et **Flask-Login** (pour la gestion des sessions). J'ai également intégré **Bootstrap** pour que l'interface soit propre et responsive sans avoir à écrire de CSS complexe.

### 1. Prérequis et Structure des fichiers

Créez un dossier pour votre projet et respectez cette structure :
```text
mon_projet/
│
├── app.py
├── requirements.txt
├── static/
│   └── uploads/        (Les photos de profil iront ici)
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── profile.html
    └── admin.html
```

Créez le fichier `requirements.txt` et installez les dépendances (`pip install -r requirements.txt`) :
```text
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Werkzeug==3.0.1
```

---

### 2. Le code principal : `app.py`

Ce fichier contient toute la logique back-end (base de données, routes, authentification, gestion d'images).

```python
import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cle_secrete_tres_securisee'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Créer le dossier d'upload s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODÈLE DE BASE DE DONNÉES ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_pic = db.Column(db.String(150), default='default.png')
    role = db.Column(db.String(50), default='user') # 'user' ou 'admin'
    is_active = db.Column(db.Boolean, default=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES D'AUTHENTIFICATION ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Cet email existe déjà.')
            return redirect(url_for('register'))
        
        new_user = User(email=email, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        flash('Compte créé ! Vous pouvez vous connecter.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash("Votre compte a été désactivé par un administrateur.")
                return redirect(url_for('login'))
            login_user(user)
            return redirect(url_for('profile'))
        else:
            flash('Email ou mot de passe incorrect.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ROUTE PROFIL UTILISATEUR ---
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        current_user.bio = request.form.get('bio')
        
        # Gestion de l'image
        pic = request.files.get('profile_pic')
        if pic and pic.filename != '':
            filename = secure_filename(pic.filename)
            pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_pic = filename
            
        db.session.commit()
        flash('Profil mis à jour !')
        return redirect(url_for('profile'))
        
    return render_template('profile.html')

# --- ROUTES ADMINISTRATEUR ---
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Accès refusé.')
        return redirect(url_for('profile'))
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/admin/toggle_status/<int:id>')
@login_required
def toggle_status(id):
    if current_user.role != 'admin':
        return redirect(url_for('profile'))
    user = User.query.get_or_404(id)
    if user.id != current_user.id: # Empêcher l'admin de se désactiver lui-même
        user.is_active = not user.is_active
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_role/<int:id>')
@login_required
def toggle_role(id):
    if current_user.role != 'admin':
        return redirect(url_for('profile'))
    user = User.query.get_or_404(id)
    if user.id != current_user.id:
        user.role = 'admin' if user.role == 'user' else 'user'
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

# --- INITIALISATION ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Créer un admin par défaut s'il n'y a pas d'utilisateurs
        if not User.query.first():
            admin = User(email='admin@admin.com', password=generate_password_hash('admin', method='pbkdf2:sha256'), role='admin', name='Super Admin')
            db.session.add(admin)
            db.session.commit()
            print("Compte administrateur créé : admin@admin.com / admin")
            
    app.run(debug=True)
```

---

### 3. Les Templates HTML (dans le dossier `templates/`)

#### `base.html` (Le layout principal)
```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Plateforme Utilisateurs</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">Ma Plateforme</a>
            <div class="collapse navbar-collapse">
                <ul class="navbar-nav ms-auto">
                    {% if current_user.is_authenticated %}
                        <li class="nav-item"><a class="nav-link" href="{{ url_for('profile') }}">Mon Profil</a></li>
                        {% if current_user.role == 'admin' %}
                            <li class="nav-item"><a class="nav-link text-warning" href="{{ url_for('admin_dashboard') }}">Admin</a></li>
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
    <div class="container mt-4">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-info">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

#### `login.html`
```html
{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-4">
        <h3 class="text-center">Connexion</h3>
        <form method="POST" action="/login">
            <div class="mb-3"><input type="email" name="email" class="form-control" placeholder="Email" required></div>
            <div class="mb-3"><input type="password" name="password" class="form-control" placeholder="Mot de passe" required></div>
            <button class="btn btn-primary w-100">Se connecter</button>
        </form>
    </div>
</div>
{% endblock %}
```

#### `register.html`
```html
{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-4">
        <h3 class="text-center">Inscription</h3>
        <form method="POST" action="/register">
            <div class="mb-3"><input type="email" name="email" class="form-control" placeholder="Email" required></div>
            <div class="mb-3"><input type="password" name="password" class="form-control" placeholder="Mot de passe" required></div>
            <button class="btn btn-success w-100">S'inscrire</button>
        </form>
    </div>
</div>
{% endblock %}
```

#### `profile.html`
```html
{% extends 'base.html' %}
{% block content %}
<div class="row">
    <div class="col-md-4 text-center">
        {% if current_user.profile_pic != 'default.png' %}
            <img src="{{ url_for('static', filename='uploads/' + current_user.profile_pic) }}" class="rounded-circle img-fluid mb-3" style="width: 150px; height: 150px; object-fit: cover;">
        {% else %}
            <div class="bg-secondary rounded-circle d-inline-block mb-3" style="width: 150px; height: 150px;"></div>
        {% endif %}
        <h4>{{ current_user.name or "Utilisateur sans nom" }}</h4>
        <p class="text-muted">{{ current_user.role|capitalize }}</p>
    </div>
    <div class="col-md-8">
        <h3>Modifier le profil</h3>
        <form method="POST" action="/profile" enctype="multipart/form-data">
            <div class="mb-3"><label>Nom</label><input type="text" name="name" class="form-control" value="{{ current_user.name or '' }}"></div>
            <div class="mb-3"><label>Email</label><input type="email" name="email" class="form-control" value="{{ current_user.email }}" required></div>
            <div class="mb-3"><label>Bio</label><textarea name="bio" class="form-control">{{ current_user.bio or '' }}</textarea></div>
            <div class="mb-3"><label>Photo de profil</label><input type="file" name="profile_pic" class="form-control" accept="image/*"></div>
            <button class="btn btn-primary">Enregistrer les modifications</button>
        </form>
    </div>
</div>
{% endblock %}
```

#### `admin.html`
```html
{% extends 'base.html' %}
{% block content %}
<h3>Espace Administrateur</h3>
<table class="table table-striped mt-3">
    <thead>
        <tr>
            <th>ID</th>
            <th>Email</th>
            <th>Nom</th>
            <th>Rôle</th>
            <th>Statut</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for user in users %}
        <tr>
            <td>{{ user.id }}</td>
            <td>{{ user.email }}</td>
            <td>{{ user.name or '-' }}</td>
            <td>
                <span class="badge {% if user.role == 'admin' %}bg-danger{% else %}bg-primary{% endif %}">{{ user.role }}</span>
            </td>
            <td>
                <span class="badge {% if user.is_active %}bg-success{% else %}bg-secondary{% endif %}">
                    {% if user.is_active %}Actif{% else %}Inactif{% endif %}
                </span>
            </td>
            <td>
                {% if user.id != current_user.id %}
                    <a href="{{ url_for('toggle_role', id=user.id) }}" class="btn btn-sm btn-warning">Changer Rôle</a>
                    <a href="{{ url_for('toggle_status', id=user.id) }}" class="btn btn-sm {% if user.is_active %}btn-danger{% else %}btn-success{% endif %}">
                        {% if user.is_active %}Désactiver{% else %}Activer{% endif %}
                    </a>
                {% else %}
                    <span class="text-muted">Vous-même</span>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

### 4. Comment lancer l'application

1. Ouvrez un terminal dans le dossier du projet.
2. Exécutez le script : `python app.py`
3. Ouvrez votre navigateur et allez sur `http://127.0.0.1:5000`

**Note :** Lors du tout premier lancement, le code va créer la base de données SQLite et générer un compte administrateur par défaut :
* **Email :** `admin@admin.com`
* **Mot de passe :** `admin`