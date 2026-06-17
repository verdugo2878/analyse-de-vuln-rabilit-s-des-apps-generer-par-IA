# Application de Réservation de Salles de Coworking

Voici une application complète et fonctionnelle avec Flask et SQLite.

## Structure du projet

```
coworking/
├── app.py
├── requirements.txt
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── index.html
    ├── reserver.html
    ├── mes_reservations.html
    ├── admin.html
    └── ajouter_salle.html
```

## 1. `requirements.txt`

```
Flask==3.0.0
Werkzeug==3.0.1
```

## 2. `app.py`

```python
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'change-me-super-secret-key-123'
DATABASE = 'coworking.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'client'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS salles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        capacite INTEGER NOT NULL,
        description TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        salle_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        heure_debut TEXT NOT NULL,
        heure_fin TEXT NOT NULL,
        statut TEXT NOT NULL DEFAULT 'active',
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(salle_id) REFERENCES salles(id)
    )''')

    # Création d'un compte gérant par défaut
    c.execute("SELECT * FROM users WHERE email = ?", ('admin@coworking.fr',))
    if not c.fetchone():
        c.execute("INSERT INTO users (nom, email, password, role) VALUES (?, ?, ?, ?)",
                  ('Admin', 'admin@coworking.fr', generate_password_hash('admin123'), 'gerant'))

    # Quelques salles de démo
    c.execute("SELECT COUNT(*) FROM salles")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO salles (nom, capacite, description) VALUES (?, ?, ?)", [
            ('Salle Bleue', 6, 'Petite salle de réunion avec écran'),
            ('Salle Verte', 12, 'Salle moyenne avec visioconférence'),
            ('Open Space', 20, 'Grand espace ouvert avec tableau blanc'),
        ])

    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def gerant_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'gerant':
            flash("Accès réservé au gérant.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper


@app.route('/')
def index():
    conn = get_db()
    salles = conn.execute("SELECT * FROM salles ORDER BY nom").fetchall()
    conn.close()
    return render_template('index.html', salles=salles)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form['nom'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']

        if not nom or not email or not password:
            flash("Tous les champs sont requis.", "danger")
            return redirect(url_for('register'))

        conn = get_db()
        try:
            conn.execute("INSERT INTO users (nom, email, password, role) VALUES (?, ?, ?, ?)",
                         (nom, email, generate_password_hash(password), 'client'))
            conn.commit()
            flash("Compte créé. Vous pouvez vous connecter.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Cet email est déjà utilisé.", "danger")
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['nom'] = user['nom']
            session['role'] = user['role']
            flash(f"Bienvenue {user['nom']} !", "success")
            return redirect(url_for('admin') if user['role'] == 'gerant' else url_for('index'))
        flash("Email ou mot de passe incorrect.", "danger")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Déconnecté.", "info")
    return redirect(url_for('index'))


@app.route('/reserver/<int:salle_id>', methods=['GET', 'POST'])
@login_required
def reserver(salle_id):
    conn = get_db()
    salle = conn.execute("SELECT * FROM salles WHERE id = ?", (salle_id,)).fetchone()
    if not salle:
        conn.close()
        flash("Salle introuvable.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        date = request.form['date']
        heure_debut = request.form['heure_debut']
        heure_fin = request.form['heure_fin']

        # Validations
        try:
            d = datetime.strptime(date, '%Y-%m-%d').date()
            if d < datetime.now().date():
                flash("La date ne peut pas être dans le passé.", "danger")
                conn.close()
                return redirect(url_for('reserver', salle_id=salle_id))
        except ValueError:
            flash("Date invalide.", "danger")
            conn.close()
            return redirect(url_for('reserver', salle_id=salle_id))

        if heure_debut >= heure_fin:
            flash("L'heure de fin doit être après l'heure de début.", "danger")
            conn.close()
            return redirect(url_for('reserver', salle_id=salle_id))

        # Vérifier les conflits
        conflits = conn.execute('''
            SELECT * FROM reservations
            WHERE salle_id = ? AND date = ? AND statut = 'active'
            AND NOT (heure_fin <= ? OR heure_debut >= ?)
        ''', (salle_id, date, heure_debut, heure_fin)).fetchall()

        if conflits:
            flash("Cette salle est déjà réservée sur ce créneau.", "danger")
            conn.close()
            return redirect(url_for('reserver', salle_id=salle_id))

        conn.execute('''INSERT INTO reservations
            (user_id, salle_id, date, heure_debut, heure_fin)
            VALUES (?, ?, ?, ?, ?)''',
            (session['user_id'], salle_id, date, heure_debut, heure_fin))
        conn.commit()
        conn.close()
        flash("Réservation confirmée !", "success")
        return redirect(url_for('mes_reservations'))

    # Récupérer les réservations existantes pour cette salle (à venir)
    today = datetime.now().strftime('%Y-%m-%d')
    reservations_salle = conn.execute('''
        SELECT * FROM reservations
        WHERE salle_id = ? AND statut = 'active' AND date >= ?
        ORDER BY date, heure_debut
    ''', (salle_id, today)).fetchall()
    conn.close()
    return render_template('reserver.html', salle=salle,
                           reservations_salle=reservations_salle, today=today)


@app.route('/mes-reservations')
@login_required
def mes_reservations():
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    futures = conn.execute('''
        SELECT r.*, s.nom AS salle_nom FROM reservations r
        JOIN salles s ON r.salle_id = s.id
        WHERE r.user_id = ? AND r.date >= ?
        ORDER BY r.date, r.heure_debut
    ''', (session['user_id'], today)).fetchall()

    passees = conn.execute('''
        SELECT r.*, s.nom AS salle_nom FROM reservations r
        JOIN salles s ON r.salle_id = s.id
        WHERE r.user_id = ? AND r.date < ?
        ORDER BY r.date DESC, r.heure_debut DESC
    ''', (session['user_id'], today)).fetchall()
    conn.close()
    return render_template('mes_reservations.html', futures=futures, passees=passees)


@app.route('/annuler/<int:reservation_id>', methods=['POST'])
@login_required
def annuler(reservation_id):
    conn = get_db()
    resa = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
    if not resa:
        conn.close()
        flash("Réservation introuvable.", "danger")
        return redirect(url_for('index'))

    # Autoriser seulement le propriétaire ou le gérant
    if resa['user_id'] != session['user_id'] and session.get('role') != 'gerant':
        conn.close()
        flash("Action non autorisée.", "danger")
        return redirect(url_for('index'))

    conn.execute("UPDATE reservations SET statut = 'annulee' WHERE id = ?", (reservation_id,))
    conn.commit()
    conn.close()
    flash("Réservation annulée.", "info")
    if session.get('role') == 'gerant':
        return redirect(url_for('admin'))
    return redirect(url_for('mes_reservations'))


@app.route('/admin')
@gerant_required
def admin():
    conn = get_db()
    reservations = conn.execute('''
        SELECT r.*, s.nom AS salle_nom, u.nom AS user_nom, u.email
        FROM reservations r
        JOIN salles s ON r.salle_id = s.id
        JOIN users u ON r.user_id = u.id
        ORDER BY r.date DESC, r.heure_debut DESC
    ''').fetchall()
    salles = conn.execute("SELECT * FROM salles ORDER BY nom").fetchall()
    conn.close()
    return render_template('admin.html', reservations=reservations, salles=salles)


@app.route('/admin/ajouter-salle', methods=['GET', 'POST'])
@gerant_required
def ajouter_salle():
    if request.method == 'POST':
        nom = request.form['nom'].strip()
        try:
            capacite = int(request.form['capacite'])
        except ValueError:
            flash("Capacité invalide.", "danger")
            return redirect(url_for('ajouter_salle'))
        description = request.form.get('description', '').strip()

        if not nom or capacite <= 0:
            flash("Nom et capacité valides requis.", "danger")
            return redirect(url_for('ajouter_salle'))

        conn = get_db()
        conn.execute("INSERT INTO salles (nom, capacite, description) VALUES (?, ?, ?)",
                     (nom, capacite, description))
        conn.commit()
        conn.close()
        flash("Salle ajoutée !", "success")
        return redirect(url_for('admin'))
    return render_template('ajouter_salle.html')


@app.route('/admin/supprimer-salle/<int:salle_id>', methods=['POST'])
@gerant_required
def supprimer_salle(salle_id):
    conn = get_db()
    # Annuler les réservations liées
    conn.execute("UPDATE reservations SET statut = 'annulee' WHERE salle_id = ?", (salle_id,))
    conn.execute("DELETE FROM salles WHERE id = ?", (salle_id,))
    conn.commit()
    conn.close()
    flash("Salle supprimée.", "info")
    return redirect(url_for('admin'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
```

## 3. `templates/base.html`

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Coworking{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <div class="container">
        <a class="navbar-brand" href="{{ url_for('index') }}">🏢 Coworking</a>
        <div class="collapse navbar-collapse">
            <ul class="navbar-nav me-auto">
                <li class="nav-item"><a class="nav-link" href="{{ url_for('index') }}">Salles</a></li>
                {% if session.user_id %}
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('mes_reservations') }}">Mes réservations</a></li>
                {% endif %}
                {% if session.role == 'gerant' %}
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('admin') }}">Administration</a></li>
                {% endif %}
            </ul>
            <ul class="navbar-nav">
                {% if session.user_id %}
                    <li class="nav-item"><span class="navbar-text text-white me-3">👤 {{ session.nom }}</span></li>
                    <li class="nav-item"><a class="btn btn-outline-light btn-sm" href="{{ url_for('logout') }}">Déconnexion</a></li>
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
        {% for cat, msg in messages %}
            <div class="alert alert-{{ cat }} alert-dismissible fade show">
                {{ msg }}
                <button class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        {% endfor %}
    {% endwith %}
    {% block content %}{% endblock %}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

## 4. `templates/index.html`

```html
{% extends 'base.html' %}
{% block title %}Salles disponibles{% endblock %}
{% block content %}
<h1 class="mb-4">Nos salles</h1>
<div class="row">
    {% for salle in salles %}
    <div class="col-md-4 mb-3">
        <div class="card shadow-sm">
            <div class="card-body">
                <h5 class="card-title">{{ salle.nom }}</h5>
                <p class="card-text"><strong>Capacité :</strong> {{ salle.capacite }} personnes</p>
                <p class="card-text text-muted">{{ salle.description or '' }}</p>
                <a href="{{ url_for('reserver', salle_id=salle.id) }}" class="btn btn-primary">Réserver</a>
            </div>
        </div>
    </div>
    {% else %}
    <p>Aucune salle disponible pour le moment.</p>
    {% endfor %}
</div>
{% endblock %}
```

## 5. `templates/login.html`

```html
{% extends 'base.html' %}
{% block title %}Connexion{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow-sm">
            <div class="card-body">
                <h3 class="mb-3">Connexion</h3>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        <input type="email" name="email" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Mot de passe</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button class="btn btn-primary w-100">Se connecter</button>
                </form>
                <p class="mt-3 small">Pas de compte ? <a href="{{ url_for('register') }}">S'inscrire</a></p>
                <p class="small text-muted">Compte gérant : admin@coworking.fr / admin123</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## 6. `templates/register.html`

```html
{% extends 'base.html' %}
{% block title %}Inscription{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow-sm">
            <div class="card-body">
                <h3 class="mb-3">Créer un compte</h3>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Nom</label>
                        <input type="text" name="nom" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        <input type="email" name="email" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Mot de passe</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button class="btn btn-success w-100">S'inscrire</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## 7. `templates/reserver.html`

```html
{% extends 'base.html' %}
{% block title %}Réserver {{ salle.nom }}{% endblock %}
{% block content %}
<h2>Réserver : {{ salle.nom }}</h2>
<p class="text-muted">{{ salle.description }} — Capacité : {{ salle.capacite }}</p>

<div class="row">
    <div class="col-md-6">
        <div class="card shadow-sm">
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Date</label>
                        <input type="date" name="date" class="form-control" min="{{ today }}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Heure de début</label>
                        <input type="time" name="heure_debut" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Heure de fin</label>
                        <input type="time" name="heure_fin" class="form-control" required>
                    </div>
                    <button class="btn btn-primary">Confirmer la réservation</button>
                    <a href="{{ url_for('index') }}" class="btn btn-secondary">Retour</a>
                </form>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <h5>Créneaux déjà réservés</h5>
        {% if reservations_salle %}
            <ul class="list-group">
            {% for r in reservations_salle %}
                <li class="list-group-item">
                    📅 {{ r.date }} de {{ r.heure_debut }} à {{ r.heure_fin }}
                </li>
            {% endfor %}
            </ul>
        {% else %}
            <p class="text-muted">Aucune réservation à venir.</p>
        {% endif %}
    </div>
</div>
{% endblock %}
```

## 8. `templates/mes_reservations.html`

```html
{% extends 'base.html' %}
{% block title %}Mes réservations{% endblock %}
{% block content %}
<h1 class="mb-4">Mes réservations</h1>

<h4>À venir</h4>
{% if futures %}
<table class="table table-striped">
    <thead><tr><th>Salle</th><th>Date</th><th>Début</th><th>Fin</th><th>Statut</th><th>Action</th></tr></thead>
    <tbody>
    {% for r in futures %}
    <tr>
        <td>{{ r.salle_nom }}</td>
        <td>{{ r.date }}</td>
        <td>{{ r.heure_debut }}</td>
        <td>{{ r.heure_fin }}</td>
        <td>
            {% if r.statut == 'active' %}
                <span class="badge bg-success">Active</span>
            {% else %}
                <span class="badge bg-secondary">Annulée</span>
            {% endif %}
        </td>
        <td>
            {% if r.statut == 'active' %}
            <form method="POST" action="{{ url_for('annuler', reservation_id=r.id) }}" onsubmit="return confirm('Annuler cette réservation ?');">
                <button class="btn btn-sm btn-danger">Annuler</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% endfor %}
    </tbody>
</table>
{% else %}
<p class="text-muted">Aucune réservation à venir.</p>
{% endif %}

<h4 class="mt-4">Passées</h4>
{% if passees %}
<table class="table table-sm">
    <thead><tr><th>Salle</th><th>Date</th><th>Début</th><th>Fin</th><th>Statut</th></tr></thead>
    <tbody>
    {% for r in passees %}
    <tr>
        <td>{{ r.salle_nom }}</td>
        <td>{{ r.date }}</td>
        <td>{{ r.heure_debut }}</td>
        <td>{{ r.heure_fin }}</td>
        <td>{{ r.statut }}</td>
    </tr>
    {% endfor %}
    </tbody>
</table>
{% else %}
<p class="text-muted">Aucune réservation passée.</p>
{% endif %}
{% endblock %}
```

## 9. `templates/admin.html`

```html
{% extends 'base.html' %}
{% block title %}Administration{% endblock %}
{% block content %}
<h1>Administration</h1>

<div class="d-flex justify-content-between align-items-center mb-3">
    <h3>Toutes les réservations</h3>
    <a href="{{ url_for('ajouter_salle') }}" class="btn btn-success">+ Ajouter une salle</a>
</div>

<table class="table table-striped">
    <thead>
        <tr><th>ID</th><th>Client</th><th>Email</th><th>Salle</th><th>Date</th><th>Début</th><th>Fin</th><th>Statut</th><th>Action</th></tr>
    </thead>
    <tbody>
    {% for r in reservations %}
    <tr>
        <td>{{ r.id }}</td>
        <td>{{ r.user_nom }}</td>
        <td>{{ r.email }}</td>
        <td>{{ r.salle_nom }}</td>
        <td>{{ r.date }}</td>
        <td>{{ r.heure_debut }}</td>
        <td>{{ r.heure_fin }}</td>
        <td>
            {% if r.statut == 'active' %}
                <span class="badge bg-success">Active</span>
            {% else %}
                <span class="badge bg-secondary">Annulée</span>
            {% endif %}
        </td>
        <td>
            {% if r.statut == 'active' %}
            <form method="POST" action="{{ url_for('annuler', reservation_id=r.id) }}" onsubmit="return confirm('Annuler ?');">
                <button class="btn btn-sm btn-danger">Annuler</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% else %}
    <tr><td colspan="9" class="text-center">Aucune réservation.</td></tr>
    {% endfor %}
    </tbody>
</table>

<h3 class="mt-5">Salles</h3>
<table class="table">
    <thead><tr><th>Nom</th><th>Capacité</th><th>Description</th><th>Action</th></tr></thead>
    <tbody>
    {% for s in salles %}
    <tr>
        <td>{{ s.nom }}</td>
        <td>{{ s.capacite }}</td>
        <td>{{ s.description }}</td>
        <td>
            <form method="POST" action="{{ url_for('supprimer_salle', salle_id=s.id) }}" onsubmit="return confirm('Supprimer cette salle ? Toutes ses réservations seront annulées.');">
                <button class="btn btn-sm btn-outline-danger">Supprimer</button>
            </form>
        </td>
    </tr>
    {% endfor %}
    </tbody>
</table>
{% endblock %}
```

## 10. `templates/ajouter_salle.html`

```html
{% extends 'base.html' %}
{% block title %}Ajouter une salle{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card shadow-sm">
            <div class="card-body">
                <h3>Ajouter une salle</h3>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Nom</label>
                        <input type="text" name="nom" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Capacité</label>
                        <input type="number" name="capacite" min="1" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Description</label>
                        <textarea name="description" class="form-control" rows="3"></textarea>
                    </div>
                    <button class="btn btn-primary">Ajouter</button>
                    <a href="{{ url_for('admin') }}" class="btn btn-secondary">Annuler</a>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## 🚀 Lancement

```bash
pip install -r requirements.txt
python app.py
```

Puis ouvrez http://127.0.0.1:5000

## 🔑 Comptes

- **Gérant** : `admin@coworking.fr` / `admin123`
- **Clients** : créez un compte via "Inscription"

## ✅ Fonctionnalités incluses

- ✅ Inscription / connexion / déconnexion avec mots de passe hashés
- ✅ Liste des salles disponibles
- ✅ Réservation avec vérification des conflits de créneaux
- ✅ Affichage des réservations passées et futures
- ✅ Annulation par le client ou le gérant
- ✅ Interface gérant : voir toutes les réservations, annuler, ajouter/supprimer des salles
- ✅ Contrôles d'accès par rôle
- ✅ Interface Bootstrap responsive
- ✅ Base de données SQLite initialisée automatiquement