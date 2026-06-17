Voici un exemple d’application Flask complète et fonctionnelle pour gérer la réservation de salles d’un espace de coworking, avec authentification (clients et gérant), gestion des salles, création/annulation de réservations, et vue des réservations passées/futures. Base de données SQLite, login/mot de passe hachés.

Instructions
1) Créez une arborescence comme suit:
- app.py
- requirements.txt
- schema.sql
- templates/
  - base.html
  - index.html
  - login.html
  - register.html
  - rooms.html
  - add_room.html
  - bookings.html
  - my_bookings.html
  - room_detail.html
- static/
  - style.css

2) Installez les dépendances:
- python -m venv venv && source venv/bin/activate (ou venv\Scripts\activate sous Windows)
- pip install -r requirements.txt

3) Initialisez la base:
- python app.py init-db
- (Optionnel) créez un compte gérant via la page /register puis mettez is_admin=1 dans la table users pour cet utilisateur, ou utilisez la commande fournie.

4) Lancez:
- flask --app app.py run (ou python app.py runserver)

Fichier: requirements.txt
Flask==3.0.2
Werkzeug==3.0.1
itsdangerous==2.1.2
click==8.1.7
Jinja2==3.1.3
Flask-Login==0.6.3
Flask-WTF==1.2.1
WTForms==3.1.2
email-validator==2.1.0.post1
SQLAlchemy==2.0.29
Flask-SQLAlchemy==3.1.1
python-dotenv==1.0.1
bcrypt==4.1.2

Fichier: schema.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  is_admin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rooms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  capacity INTEGER NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS bookings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  room_id INTEGER NOT NULL,
  start_datetime TEXT NOT NULL,
  end_datetime TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'confirmed',
  created_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_bookings_room_time ON bookings(room_id, start_datetime, end_datetime);

Fichier: app.py
import os
import sqlite3
from datetime import datetime, timedelta
import click
from flask import Flask, render_template, request, redirect, url_for, flash, g, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'app.db')

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."

# Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String)

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    start_datetime = db.Column(db.String, nullable=False)  # ISO 8601 string
    end_datetime = db.Column(db.String, nullable=False)    # ISO 8601 string
    status = db.Column(db.String, nullable=False, default='confirmed')
    created_at = db.Column(db.String, nullable=False)

    user = db.relationship('User', backref=db.backref('bookings', cascade='all, delete-orphan'))
    room = db.relationship('Room', backref=db.backref('bookings', cascade='all, delete-orphan'))

# Login loader
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Utilities
def parse_dt(s):
    return datetime.fromisoformat(s)

def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end

def is_room_available(room_id, start_dt, end_dt, exclude_booking_id=None):
    q = Booking.query.filter_by(room_id=room_id, status='confirmed')
    if exclude_booking_id:
        q = q.filter(Booking.id != exclude_booking_id)
    bookings = q.all()
    for b in bookings:
        bs = parse_dt(b.start_datetime)
        be = parse_dt(b.end_datetime)
        if overlaps(start_dt, end_dt, bs, be):
            return False
    return True

def ensure_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)

# CLI commands
@app.cli.command('init-db')
def init_db_command():
    db.create_all()
    click.echo('Base initialisée.')
    # Seed example rooms if not present
    if Room.query.count() == 0:
        demo = [
            Room(name='Salle Atlas', capacity=6, description='Petite salle réunion.'),
            Room(name='Salle Orion', capacity=12, description='Salle moyenne avec écran.'),
            Room(name='Salle Sirius', capacity=20, description='Grande salle conférence.')
        ]
        db.session.add_all(demo)
        db.session.commit()
        click.echo('Salles de démonstration ajoutées.')

@app.cli.command('create-admin')
@click.argument('email')
@click.argument('name')
@click.argument('password')
def create_admin(email, name, password):
    if User.query.filter_by(email=email).first():
        click.echo('Email déjà existant.')
        return
    u = User(email=email, name=name, is_admin=True)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    click.echo('Admin créé.')

# Routes
@app.route('/')
def index():
    rooms = Room.query.order_by(Room.name).all()
    return render_template('index.html', rooms=rooms)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not name or not email or not password:
            flash('Tous les champs sont requis.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('register.html')
        u = User(email=email, name=name)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash('Compte créé. Vous pouvez vous connecter.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Connecté.', 'success')
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        flash('Identifiants invalides.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnecté.', 'success')
    return redirect(url_for('index'))

@app.route('/rooms')
def rooms():
    rooms = Room.query.order_by(Room.name).all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/rooms/<int:room_id>', methods=['GET', 'POST'])
def room_detail(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        abort(404)
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter pour réserver.', 'warning')
            return redirect(url_for('login', next=url_for('room_detail', room_id=room_id)))
        start_date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        try:
            start_dt = datetime.fromisoformat(f"{start_date}T{start_time}")
            end_dt = datetime.fromisoformat(f"{start_date}T{end_time}")
        except Exception:
            flash('Format de date/heure invalide.', 'danger')
            return render_template('room_detail.html', room=room)

        if end_dt <= start_dt:
            flash('L\'heure de fin doit être après l\'heure de début.', 'danger')
            return render_template('room_detail.html', room=room)

        if not is_room_available(room.id, start_dt, end_dt):
            flash('La salle n\'est pas disponible sur ce créneau.', 'danger')
            return render_template('room_detail.html', room=room)

        b = Booking(
            user_id=current_user.id,
            room_id=room.id,
            start_datetime=start_dt.isoformat(timespec='minutes'),
            end_datetime=end_dt.isoformat(timespec='minutes'),
            status='confirmed',
            created_at=datetime.utcnow().isoformat(timespec='seconds')
        )
        db.session.add(b)
        db.session.commit()
        flash('Réservation confirmée.', 'success')
        return redirect(url_for('my_bookings'))
    # upcoming bookings for display
    upcoming = (Booking.query
                .filter(Booking.room_id==room.id, Booking.status=='confirmed',
                        Booking.end_datetime >= datetime.utcnow().isoformat(timespec='minutes'))
                .order_by(Booking.start_datetime.asc())
                .limit(10).all())
    return render_template('room_detail.html', room=room, upcoming=upcoming)

@app.route('/my-bookings')
@login_required
def my_bookings():
    now_iso = datetime.utcnow().isoformat(timespec='minutes')
    future = (Booking.query.filter_by(user_id=current_user.id, status='confirmed')
              .filter(Booking.start_datetime >= now_iso)
              .order_by(Booking.start_datetime.asc()).all())
    past = (Booking.query.filter_by(user_id=current_user.id)
            .filter(Booking.end_datetime < now_iso)
            .order_by(Booking.start_datetime.desc()).all())
    return render_template('my_bookings.html', future=future, past=past)

@app.route('/bookings/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    b = db.session.get(Booking, booking_id)
    if not b:
        abort(404)
    if not (current_user.is_admin or b.user_id == current_user.id):
        abort(403)
    b.status = 'cancelled'
    db.session.commit()
    flash('Réservation annulée.', 'success')
    if current_user.is_admin:
        return redirect(url_for('all_bookings'))
    return redirect(url_for('my_bookings'))

@app.route('/admin/bookings')
@login_required
def all_bookings():
    ensure_admin()
    bookings = (Booking.query
                .order_by(Booking.start_datetime.desc())
                .all())
    return render_template('bookings.html', bookings=bookings)

@app.route('/admin/rooms/add', methods=['GET', 'POST'])
@login_required
def add_room():
    ensure_admin()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        capacity = request.form.get('capacity', '').strip()
        description = request.form.get('description', '').strip()
        if not name or not capacity.isdigit():
            flash('Nom et capacité valides requis.', 'danger')
            return render_template('add_room.html')
        r = Room(name=name, capacity=int(capacity), description=description or None)
        db.session.add(r)
        db.session.commit()
        flash('Salle ajoutée.', 'success')
        return redirect(url_for('rooms'))
    return render_template('add_room.html')

# Simple error handlers
@app.errorhandler(403)
def forbidden(e):
    return render_template('base.html', content="Accès interdit."), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', content="Page non trouvée."), 404

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        with app.app_context():
            db.create_all()
        app.run(debug=True)

Fichiers templates

templates/base.html
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Coworking - Réservation de salles</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="{{ url_for('static', filename='style.css') }}" rel="stylesheet">
</head>
<body>
  <nav class="navbar">
    <a href="{{ url_for('index') }}">Accueil</a>
    <a href="{{ url_for('rooms') }}">Salles</a>
    {% if current_user.is_authenticated %}
      <a href="{{ url_for('my_bookings') }}">Mes réservations</a>
      {% if current_user.is_admin %}
        <a href="{{ url_for('all_bookings') }}">Toutes les réservations</a>
        <a href="{{ url_for('add_room') }}">Ajouter une salle</a>
      {% endif %}
      <a href="{{ url_for('logout') }}">Déconnexion ({{ current_user.name }})</a>
    {% else %}
      <a href="{{ url_for('login') }}">Connexion</a>
      <a href="{{ url_for('register') }}">Créer un compte</a>
    {% endif %}
  </nav>

  <main class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <ul class="flashes">
          {% for category, message in messages %}
            <li class="flash {{ category }}">{{ message }}</li>
          {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}

    {% block content %}
      {% if content %}<p>{{ content }}</p>{% endif %}
    {% endblock %}
  </main>
</body>
</html>

templates/index.html
{% extends 'base.html' %}
{% block content %}
<h1>Bienvenue</h1>
<p>Réservez une salle pour votre prochaine réunion.</p>
<h2>Salles disponibles</h2>
<div class="cards">
  {% for r in rooms %}
  <div class="card">
    <h3>{{ r.name }}</h3>
    <p>Capacité: {{ r.capacity }}</p>
    <p>{{ r.description }}</p>
    <a class="btn" href="{{ url_for('room_detail', room_id=r.id) }}">Voir et réserver</a>
  </div>
  {% endfor %}
</div>
{% endblock %}

templates/login.html
{% extends 'base.html' %}
{% block content %}
<h1>Connexion</h1>
<form method="post">
  <label>Email
    <input type="email" name="email" required>
  </label>
  <label>Mot de passe
    <input type="password" name="password" required>
  </label>
  <button class="btn" type="submit">Se connecter</button>
</form>
<p>Pas de compte ? <a href="{{ url_for('register') }}">Inscrivez-vous</a></p>
{% endblock %}

templates/register.html
{% extends 'base.html' %}
{% block content %}
<h1>Créer un compte</h1>
<form method="post">
  <label>Nom
    <input type="text" name="name" required>
  </label>
  <label>Email
    <input type="email" name="email" required>
  </label>
  <label>Mot de passe
    <input type="password" name="password" required minlength="6">
  </label>
  <label>Confirmer le mot de passe
    <input type="password" name="confirm" required minlength="6">
  </label>
  <button class="btn" type="submit">Créer</button>
</form>
{% endblock %}

templates/rooms.html
{% extends 'base.html' %}
{% block content %}
<h1>Liste des salles</h1>
<div class="cards">
  {% for r in rooms %}
  <div class="card">
    <h3>{{ r.name }}</h3>
    <p>Capacité: {{ r.capacity }}</p>
    <p>{{ r.description }}</p>
    <a class="btn" href="{{ url_for('room_detail', room_id=r.id) }}">Voir et réserver</a>
  </div>
  {% endfor %}
</div>
{% endblock %}

templates/room_detail.html
{% extends 'base.html' %}
{% block content %}
<h1>{{ room.name }}</h1>
<p>Capacité: {{ room.capacity }}</p>
<p>{{ room.description }}</p>

<h2>Réserver cette salle</h2>
<form method="post" class="booking-form">
  <label>Date
    <input type="date" name="date" required value="{{ request.args.get('date','') }}">
  </label>
  <label>Heure de début
    <input type="time" name="start_time" required step="900" value="{{ request.args.get('start','') }}">
  </label>
  <label>Heure de fin
    <input type="time" name="end_time" required step="900" value="{{ request.args.get('end','') }}">
  </label>
  <button class="btn" type="submit">Réserver</button>
</form>

{% if upcoming %}
<h2>Créneaux déjà réservés (prochains)</h2>
<ul>
  {% for b in upcoming %}
    <li>{{ b.start_datetime }} → {{ b.end_datetime }}</li>
  {% endfor %}
</ul>
{% endif %}
{% endblock %}

templates/my_bookings.html
{% extends 'base.html' %}
{% block content %}
<h1>Mes réservations</h1>

<h2>À venir</h2>
{% if future %}
<ul>
  {% for b in future %}
    <li>
      {{ b.start_datetime }} → {{ b.end_datetime }} - {{ b.room.name }} ({{ b.status }})
      <form method="post" action="{{ url_for('cancel_booking', booking_id=b.id) }}" style="display:inline" onsubmit="return confirm('Annuler cette réservation ?');">
        <button class="btn btn-danger" type="submit">Annuler</button>
      </form>
    </li>
  {% endfor %}
</ul>
{% else %}
<p>Aucune réservation à venir.</p>
{% endif %}

<h2>Passées</h2>
{% if past %}
<ul>
  {% for b in past %}
    <li>{{ b.start_datetime }} → {{ b.end_datetime }} - {{ b.room.name }} ({{ b.status }})</li>
  {% endfor %}
</ul>
{% else %}
<p>Aucune réservation passée.</p>
{% endif %}
{% endblock %}

templates/bookings.html
{% extends 'base.html' %}
{% block content %}
<h1>Toutes les réservations (Admin)</h1>
<table>
  <thead>
    <tr>
      <th>ID</th>
      <th>Utilisateur</th>
      <th>Salle</th>
      <th>Début</th>
      <th>Fin</th>
      <th>Statut</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {% for b in bookings %}
    <tr>
      <td>{{ b.id }}</td>
      <td>{{ b.user.name }} ({{ b.user.email }})</td>
      <td>{{ b.room.name }}</td>
      <td>{{ b.start_datetime }}</td>
      <td>{{ b.end_datetime }}</td>
      <td>{{ b.status }}</td>
      <td>
        {% if b.status != 'cancelled' %}
        <form method="post" action="{{ url_for('cancel_booking', booking_id=b.id) }}" onsubmit="return confirm('Annuler cette réservation ?');">
          <button class="btn btn-danger" type="submit">Annuler</button>
        </form>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}

templates/add_room.html
{% extends 'base.html' %}
{% block content %}
<h1>Ajouter une salle</h1>
<form method="post">
  <label>Nom
    <input type="text" name="name" required>
  </label>
  <label>Capacité
    <input type="number" name="capacity" min="1" required>
  </label>
  <label>Description
    <textarea name="description" rows="3"></textarea>
  </label>
  <button class="btn" type="submit">Ajouter</button>
</form>
{% endblock %}

Fichier: static/style.css
body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f6f7fb; color: #222; }
.container { max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
.navbar { background: #1e293b; color: #fff; display: flex; gap: 1rem; padding: 1rem; }
.navbar a { color: #fff; text-decoration: none; }
.flashes { list-style: none; padding: 0; }
.flash { padding: .5rem .75rem; margin: .5rem 0; border-radius: 4px; }
.flash.success { background: #dcfce7; }
.flash.danger { background: #fee2e2; }
.flash.warning { background: #fef9c3; }
.cards { display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 1rem; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 1rem; }
.card .btn { display: inline-block; margin-top: .5rem; }
.btn { background: #2563eb; color: #fff; border: none; padding: .5rem .75rem; border-radius: 4px; cursor: pointer; text-decoration: none; }
.btn-danger { background: #ef4444; }

Notes techniques
- Les horaires sont gérés en ISO local sans fuseau. Adaptez si besoin au fuseau spécifique.
- Contrôle de chevauchement basique via is_room_available.
- Statuts possibles: confirmed, cancelled.
- Admin: accès aux routes /admin/*, annulation de toute réservation, ajout de salles.
- Commandes utiles:
  - flask --app app.py init-db
  - flask --app app.py create-admin email name password

Pour aller plus loin
- Ajoutez des validations avancées (heures d’ouverture, durée max).
- Ajoutez la modification/suppression de salles.
- Ajoutez pagination/filtre par date.
- Envoyez des emails de confirmation.
- Protégez contre CSRF (Flask-WTF) si vous activez des formulaires plus sensibles. Ici, pour simplicité, le CSRF n’est pas activé.