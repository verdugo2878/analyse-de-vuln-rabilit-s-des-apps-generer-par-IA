Voici une application web complète et fonctionnelle en Python avec Flask, SQLAlchemy (pour SQLite) et Flask-Login (pour l'authentification). Elle utilise Bootstrap pour une interface claire et responsive.

### 1. Préparation

Créez un dossier pour votre projet et installez les dépendances nécessaires :

```bash
mkdir coworking_app
cd coworking_app
pip install flask flask-sqlalchemy flask-login werkzeug
```

Créez l'arborescence suivante :
```text
coworking_app/
│── app.py
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── admin.html
    └── book.html
```

### 2. Le code Python (`app.py`)

Ce fichier contient la configuration, les modèles de base de données et toutes les routes. Il créera automatiquement la base de données et un compte administrateur au premier lancement.

```python
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coworking.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Modèles de base de données ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    reservations = db.relationship('Reservation', backref='user', lazy=True)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    reservations = db.relationship('Reservation', backref='room', lazy=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes Authentification ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash("Nom d'utilisateur déjà pris.", "danger")
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Compte créé avec succès ! Connectez-vous.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("Identifiants incorrects.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- Routes Client ---
@app.route('/')
def index():
    rooms = Room.query.all()
    return render_template('index.html', rooms=rooms)

@app.route('/book/<int:room_id>', methods=['GET', 'POST'])
@login_required
def book(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        date_str = request.form.get('date')
        start_str = request.form.get('start_time')
        end_str = request.form.get('end_time')
        
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_obj = datetime.strptime(start_str, '%H:%M').time()
        end_obj = datetime.strptime(end_str, '%H:%M').time()
        
        if start_obj >= end_obj:
            flash("L'heure de fin doit être après l'heure de début.", "danger")
            return redirect(url_for('book', room_id=room_id))
            
        # Vérification des conflits (simplifiée)
        conflict = Reservation.query.filter_by(room_id=room.id, date=date_obj).filter(
            (Reservation.start_time < end_obj) & (Reservation.end_time > start_obj)
        ).first()
        
        if conflict:
            flash("La salle est déjà réservée sur ce créneau.", "danger")
            return redirect(url_for('book', room_id=room_id))
            
        new_res = Reservation(date=date_obj, start_time=start_obj, end_time=end_obj, user_id=current_user.id, room_id=room.id)
        db.session.add(new_res)
        db.session.commit()
        flash("Réservation confirmée !", "success")
        return redirect(url_for('dashboard'))
        
    return render_template('book.html', room=room)

@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().date()
    # Trier par date
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.date.desc()).all()
    future_res = [r for r in reservations if r.date >= today]
    past_res = [r for r in reservations if r.date < today]
    return render_template('dashboard.html', future=future_res, past=past_res)

# --- Routes Admin ---
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        flash("Accès refusé.", "danger")
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        capacity = request.form.get('capacity')
        new_room = Room(name=name, capacity=capacity)
        db.session.add(new_room)
        db.session.commit()
        flash("Salle ajoutée.", "success")
        return redirect(url_for('admin'))
        
    reservations = Reservation.query.order_by(Reservation.date.desc()).all()
    return render_template('admin.html', reservations=reservations)

@app.route('/cancel/<int:res_id>')
@login_required
def cancel(res_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    res = Reservation.query.get_or_404(res_id)
    db.session.delete(res)
    db.session.commit()
    flash("Réservation annulée.", "success")
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Créer un admin par défaut si aucun n'existe
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password=generate_password_hash('admin', method='pbkdf2:sha256'), is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
    app.run(debug=True)
```

### 3. Les Templates HTML (dossier `templates/`)

Créez ces fichiers dans le dossier `templates`.

**`base.html`** (Le squelette du site)
```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Coworking Booking</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container">
        <a class="navbar-brand" href="{{ url_for('index') }}">Coworking</a>
        <div class="collapse navbar-collapse">
            <ul class="navbar-nav ms-auto">
                {% if current_user.is_authenticated %}
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Mes Réservations</a></li>
                    {% if current_user.is_admin %}
                        <li class="nav-item"><a class="nav-link" href="{{ url_for('admin') }}">Gestion Admin</a></li>
                    {% endif %}
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Déconnexion ({{ current_user.username }})</a></li>
                {% else %}
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Connexion</a></li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('register') }}">Inscription</a></li>
                {% endif %}
            </ul>
        </div>
    </div>
</nav>
<div class="container mt-4">
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
</div>
</body>
</html>
```

**`index.html`**
```html
{% extends "base.html" %}
{% block content %}
<h2>Salles disponibles</h2>
<div class="row mt-3">
    {% for room in rooms %}
    <div class="col-md-4 mb-3">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">{{ room.name }}</h5>
                <p class="card-text">Capacité : {{ room.capacity }} personnes</p>
                <a href="{{ url_for('book', room_id=room.id) }}" class="btn btn-primary">Réserver</a>
            </div>
        </div>
    </div>
    {% else %}
    <p>Aucune salle n'est disponible pour le moment.</p>
    {% endfor %}
</div>
{% endblock %}
```

**`login.html`**
```html
{% extends "base.html" %}
{% block content %}
<div class="col-md-6 offset-md-3">
    <h2>Connexion</h2>
    <form method="POST">
        <div class="mb-3"><label>Nom d'utilisateur</label><input type="text" name="username" class="form-control" required></div>
        <div class="mb-3"><label>Mot de passe</label><input type="password" name="password" class="form-control" required></div>
        <button type="submit" class="btn btn-success">Se connecter</button>
    </form>
</div>
{% endblock %}
```

**`register.html`**
```html
{% extends "base.html" %}
{% block content %}
<div class="col-md-6 offset-md-3">
    <h2>Inscription</h2>
    <form method="POST">
        <div class="mb-3"><label>Nom d'utilisateur</label><input type="text" name="username" class="form-control" required></div>
        <div class="mb-3"><label>Mot de passe</label><input type="password" name="password" class="form-control" required></div>
        <button type="submit" class="btn btn-primary">S'inscrire</button>
    </form>
</div>
{% endblock %}
```

**`book.html`**
```html
{% extends "base.html" %}
{% block content %}
<h2>Réserver : {{ room.name }} (Capacité: {{ room.capacity }})</h2>
<form method="POST" class="mt-3 col-md-6">
    <div class="mb-3"><label>Date</label><input type="date" name="date" class="form-control" required></div>
    <div class="mb-3"><label>Heure de début</label><input type="time" name="start_time" class="form-control" required></div>
    <div class="mb-3"><label>Heure de fin</label><input type="time" name="end_time" class="form-control" required></div>
    <button type="submit" class="btn btn-primary">Confirmer la réservation</button>
</form>
{% endblock %}
```

**`dashboard.html`**
```html
{% extends "base.html" %}
{% block content %}
<h2>Mes Réservations</h2>
<h4 class="mt-4">À venir</h4>
<table class="table table-striped">
    <tr><th>Salle</th><th>Date</th><th>Début</th><th>Fin</th></tr>
    {% for r in future %}
    <tr><td>{{ r.room.name }}</td><td>{{ r.date.strftime('%d/%m/%Y') }}</td><td>{{ r.start_time.strftime('%H:%M') }}</td><td>{{ r.end_time.strftime('%H:%M') }}</td></tr>
    {% else %}<tr><td colspan="4">Aucune réservation à venir.</td></tr>{% endfor %}
</table>

<h4 class="mt-4">Passées</h4>
<table class="table table-secondary">
    <tr><th>Salle</th><th>Date</th><th>Début</th><th>Fin</th></tr>
    {% for r in past %}
    <tr><td>{{ r.room.name }}</td><td>{{ r.date.strftime('%d/%m/%Y') }}</td><td>{{ r.start_time.strftime('%H:%M') }}</td><td>{{ r.end_time.strftime('%H:%M') }}</td></tr>
    {% else %}<tr><td colspan="4">Aucune réservation passée.</td></tr>{% endfor %}
</table>
{% endblock %}
```

**`admin.html`**
```html
{% extends "base.html" %}
{% block content %}
<h2>Espace Gérant</h2>

<div class="card mt-4 mb-4">
    <div class="card-header">Ajouter une nouvelle salle</div>
    <div class="card-body">
        <form method="POST" class="row gx-3 gy-2 align-items-center">
            <div class="col-sm-5"><input type="text" name="name" class="form-control" placeholder="Nom de la salle" required></div>
            <div class="col-sm-3"><input type="number" name="capacity" class="form-control" placeholder="Capacité" required></div>
            <div class="col-auto"><button type="submit" class="btn btn-success">Ajouter</button></div>
        </form>
    </div>
</div>

<h4>Toutes les réservations</h4>
<table class="table table-bordered">
    <tr><th>Client</th><th>Salle</th><th>Date</th><th>Horaires</th><th>Action</th></tr>
    {% for r in reservations %}
    <tr>
        <td>{{ r.user.username }}</td>
        <td>{{ r.room.name }}</td>
        <td>{{ r.date.strftime('%d/%m/%Y') }}</td>
        <td>{{ r.start_time.strftime('%H:%M') }} - {{ r.end_time.strftime('%H:%M') }}</td>
        <td><a href="{{ url_for('cancel', res_id=r.id) }}" class="btn btn-sm btn-danger" onclick="return confirm('Annuler cette réservation ?')">Annuler</a></td>
    </tr>
    {% else %}
    <tr><td colspan="5">Aucune réservation.</td></tr>
    {% endfor %}
</table>
{% endblock %}
```

### 4. Lancer l'application

1. Ouvrez votre terminal dans le dossier `coworking_app`.
2. Lancez le script : `python app.py`
3. Ouvrez votre navigateur à l'adresse : `http://127.0.0.1:5000`

**Comptes par défaut :**
* Le compte administrateur est créé automatiquement. **Nom d'utilisateur:** `admin` | **Mot de passe:** `admin` (Connectez-vous avec ce compte pour ajouter les premières salles).
* Les clients peuvent créer leur propre compte via la page "Inscription".