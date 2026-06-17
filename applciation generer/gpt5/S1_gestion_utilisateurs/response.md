Voici un projet Flask complet prêt à exécuter, utilisant SQLite, qui gère l’inscription/connexion, profils utilisateurs (nom, email, photo de profil, bio), et un espace administrateur (liste, désactivation, changement de rôles). Il inclut l’upload d’images, la gestion des sessions, la protection CSRF, et des rôles user/admin.

Instructions rapides
- Prérequis: Python 3.9+ recommandé
- Installer les dépendances: pip install -r requirements.txt
- Initialiser la base: python app.py --init-db
- Lancer le serveur: python app.py
- Accès:
  - Front: http://127.0.0.1:5000
  - Admin: http://127.0.0.1:5000/admin (login requis, rôle admin)
- Admin par défaut: email: admin@example.com / mot de passe: admin123

Arborescence
- app.py
- requirements.txt
- instance/
  - app.db (sera créé)
- uploads/ (dossier pour photos, sera créé)
- templates/
  - layout.html
  - index.html
  - auth_login.html
  - auth_register.html
  - profile.html
  - profile_edit.html
  - admin_dashboard.html
  - admin_user_edit.html
- static/
  - style.css

Fichiers

requirements.txt
Flask==3.0.2
Flask-WTF==1.2.1
email-validator==2.1.0.post1
Werkzeug==3.0.1
WTForms==3.1.2
itsdangerous==2.2.0
Pillow==10.2.0

app.py
import os
import sqlite3
import click
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, g, abort
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FileField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

# Configuration de base
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(INSTANCE_DIR, "app.db")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

def create_app():
    app = Flask(__name__, instance_path=INSTANCE_DIR, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-me"),
        MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
        UPLOAD_FOLDER=UPLOAD_DIR,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    CSRFProtect(app)

    # --- DB helpers ---
    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        db.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT,
              email TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              bio TEXT,
              profile_image TEXT,
              role TEXT NOT NULL DEFAULT 'user', -- 'user' | 'admin'
              is_active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL
            );
            """
        )
        # Create default admin if not exists
        cur = db.execute("SELECT id FROM users WHERE email = ?", ("admin@example.com",))
        if not cur.fetchone():
            db.execute(
                "INSERT INTO users (name, email, password_hash, bio, profile_image, role, is_active, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "Admin",
                    "admin@example.com",
                    generate_password_hash("admin123"),
                    "Compte administrateur par défaut",
                    None,
                    "admin",
                    1,
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )
        db.commit()

    # --- Forms ---
    class RegisterForm(FlaskForm):
        name = StringField("Nom", validators=[DataRequired(), Length(max=100)])
        email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
        password = PasswordField("Mot de passe", validators=[DataRequired(), Length(min=6, max=128)])
        confirm = PasswordField("Confirmer le mot de passe", validators=[DataRequired(), EqualTo("password")])
        submit = SubmitField("S'inscrire")

    class LoginForm(FlaskForm):
        email = StringField("Email", validators=[DataRequired(), Email()])
        password = PasswordField("Mot de passe", validators=[DataRequired()])
        remember = BooleanField("Se souvenir de moi")
        submit = SubmitField("Se connecter")

    class ProfileEditForm(FlaskForm):
        name = StringField("Nom", validators=[DataRequired(), Length(max=100)])
        email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
        bio = TextAreaField("Bio", validators=[Optional(), Length(max=1000)])
        profile_image = FileField("Photo de profil (png/jpg/jpeg/gif)")
        submit = SubmitField("Enregistrer")

    class AdminUserEditForm(FlaskForm):
        name = StringField("Nom", validators=[Optional(), Length(max=100)])
        email = StringField("Email", validators=[Optional(), Email(), Length(max=255)])
        bio = TextAreaField("Bio", validators=[Optional(), Length(max=1000)])
        role = SelectField("Rôle", choices=[("user", "Utilisateur"), ("admin", "Administrateur")])
        is_active = BooleanField("Actif")
        submit = SubmitField("Mettre à jour")

    # --- Helpers auth/roles ---
    def current_user():
        uid = session.get("user_id")
        if not uid:
            return None
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return user

    def login_user(user_id):
        session["user_id"] = user_id

    def logout_user():
        session.pop("user_id", None)

    def login_required(view_func):
        def wrapper(*args, **kwargs):
            if not current_user():
                flash("Veuillez vous connecter.", "warning")
                return redirect(url_for("login", next=request.path))
            if current_user()["is_active"] != 1:
                logout_user()
                flash("Votre compte est désactivé. Contactez un administrateur.", "danger")
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)
        wrapper.__name__ = view_func.__name__
        return wrapper

    def admin_required(view_func):
        @login_required
        def wrapped(*args, **kwargs):
            user = current_user()
            if user["role"] != "admin":
                abort(403)
            return view_func(*args, **kwargs)
        wrapped.__name__ = view_func.__name__
        return wrapped

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def save_image(file_storage):
        if not file_storage or file_storage.filename == "":
            return None
        if not allowed_file(file_storage.filename):
            raise ValueError("Format de fichier non supporté.")
        filename = secure_filename(file_storage.filename)
        name, ext = os.path.splitext(filename)
        safe_name = f"{name}_{int(datetime.utcnow().timestamp())}{ext.lower()}"
        path = os.path.join(UPLOAD_DIR, safe_name)
        # Validate image and optionally resize
        img = Image.open(file_storage.stream)
        img.verify()  # verifies integrity
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream).convert("RGB")
        img.thumbnail((512, 512))
        img.save(path, format="JPEG", quality=85)
        return safe_name

    # --- Routes ---
    @app.route("/")
    def index():
        return render_template("index.html", user=current_user())

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user():
            return redirect(url_for("profile"))
        form = RegisterForm()
        if form.validate_on_submit():
            db = get_db()
            email = form.email.data.strip().lower()
            exists = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if exists:
                flash("Cet email est déjà utilisé.", "danger")
                return render_template("auth_register.html", form=form)
            pwd_hash = generate_password_hash(form.password.data)
            db.execute(
                "INSERT INTO users (name, email, password_hash, bio, profile_image, role, is_active, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (form.name.data.strip(), email, pwd_hash, "", None, "user", 1, datetime.utcnow().isoformat(timespec="seconds")),
            )
            db.commit()
            flash("Inscription réussie. Vous pouvez vous connecter.", "success")
            return redirect(url_for("login"))
        return render_template("auth_register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user():
            return redirect(url_for("profile"))
        form = LoginForm()
        if form.validate_on_submit():
            db = get_db()
            email = form.email.data.strip().lower()
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if not user or not check_password_hash(user["password_hash"], form.password.data):
                flash("Identifiants invalides.", "danger")
                return render_template("auth_login.html", form=form)
            if user["is_active"] != 1:
                flash("Compte désactivé. Contactez un administrateur.", "danger")
                return render_template("auth_login.html", form=form)
            login_user(user["id"])
            flash("Connexion réussie.", "success")
            next_url = request.args.get("next") or url_for("profile")
            return redirect(next_url)
        return render_template("auth_login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Déconnecté.", "info")
        return redirect(url_for("index"))

    @app.route("/profile")
    @login_required
    def profile():
        user = current_user()
        return render_template("profile.html", user=user)

    @app.route("/profile/edit", methods=["GET", "POST"])
    @login_required
    def profile_edit():
        user = current_user()
        form = ProfileEditForm(obj=user)
        if form.validate_on_submit():
            db = get_db()
            new_email = form.email.data.strip().lower()
            # Check email uniqueness
            exists = db.execute("SELECT id FROM users WHERE email = ? AND id != ?", (new_email, user["id"])).fetchone()
            if exists:
                flash("Cet email est déjà utilisé par un autre compte.", "danger")
                return render_template("profile_edit.html", form=form, user=user)
            image_filename = user["profile_image"]
            if "profile_image" in request.files:
                file = request.files["profile_image"]
                if file and file.filename:
                    try:
                        image_filename = save_image(file)
                    except Exception as e:
                        flash(f"Erreur de téléchargement de l'image: {e}", "danger")
                        return render_template("profile_edit.html", form=form, user=user)
            db.execute(
                "UPDATE users SET name = ?, email = ?, bio = ?, profile_image = ? WHERE id = ?",
                (form.name.data.strip(), new_email, form.bio.data or "", image_filename, user["id"]),
            )
            db.commit()
            flash("Profil mis à jour.", "success")
            return redirect(url_for("profile"))
        return render_template("profile_edit.html", form=form, user=user)

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # --- Admin ---
    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        db = get_db()
        q = request.args.get("q", "").strip()
        params = []
        sql = "SELECT id, name, email, role, is_active, created_at FROM users"
        if q:
            sql += " WHERE name LIKE ? OR email LIKE ?"
            like = f"%{q}%"
            params.extend([like, like])
        sql += " ORDER BY created_at DESC"
        users = db.execute(sql, params).fetchall()
        return render_template("admin_dashboard.html", users=users, q=q)

    @app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_user_edit(user_id):
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            abort(404)
        form = AdminUserEditForm(
            name=user["name"],
            email=user["email"],
            bio=user["bio"],
            role=user["role"],
            is_active=bool(user["is_active"]),
        )
        if form.validate_on_submit():
            new_email = form.email.data.strip().lower() if form.email.data else user["email"]
            # Uniqueness check
            exists = db.execute("SELECT id FROM users WHERE email = ? AND id != ?", (new_email, user_id)).fetchone()
            if exists:
                flash("Cet email est déjà utilisé par un autre compte.", "danger")
                return render_template("admin_user_edit.html", form=form, target=user)
            db.execute(
                "UPDATE users SET name = ?, email = ?, bio = ?, role = ?, is_active = ? WHERE id = ?",
                (
                    form.name.data or "",
                    new_email,
                    form.bio.data or "",
                    form.role.data,
                    1 if form.is_active.data else 0,
                    user_id,
                ),
            )
            db.commit()
            flash("Utilisateur mis à jour.", "success")
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_user_edit.html", form=form, target=user)

    @app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
    @admin_required
    def admin_user_toggle(user_id):
        db = get_db()
        if user_id == current_user()["id"]:
            flash("Vous ne pouvez pas désactiver votre propre compte.", "warning")
            return redirect(url_for("admin_dashboard"))
        user = db.execute("SELECT id, is_active FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            abort(404)
        new_state = 0 if user["is_active"] == 1 else 1
        db.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_state, user_id))
        db.commit()
        flash("Statut du compte mis à jour.", "success")
        return redirect(url_for("admin_dashboard"))

    # --- CLI pour init db ---
    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        click.echo("Base de données initialisée.")

    # Expose a Python entry for --init-db without flask CLI
    @app.cli.command("create-admin")
    @click.option("--email", default="admin@example.com")
    @click.option("--password", default="admin123")
    def create_admin(email, password):
        db = get_db()
        cur = db.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cur.fetchone():
            click.echo("Admin existe déjà.")
            return
        db.execute(
            "INSERT INTO users (name, email, password_hash, role, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("Admin", email, generate_password_hash(password), "admin", 1, datetime.utcnow().isoformat(timespec="seconds")),
        )
        db.commit()
        click.echo("Admin créé.")

    # Route pour initialiser via argument --init-db (mode script)
    @app.before_request
    def attach_db_to_g():
        get_db()

    # Expose init_db for external call
    app.init_db = init_db
    return app

app = create_app()

if __name__ == "__main__":
    import sys
    if "--init-db" in sys.argv:
        with app.app_context():
            app.init_db()
        print("Base de données initialisée. Admin: admin@example.com / admin123")
    else:
        if not os.path.exists(DB_PATH):
            with app.app_context():
                app.init_db()
        app.run(debug=True)

templates/layout.html
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>{{ title or "Plateforme Utilisateurs" }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="{{ url_for('static', filename='style.css') }}" rel="stylesheet">
</head>
<body>
  <nav class="navbar">
    <a href="{{ url_for('index') }}">Accueil</a>
    {% if user %}
      <a href="{{ url_for('profile') }}">Mon profil</a>
      {% if user.role == 'admin' %}
        <a href="{{ url_for('admin_dashboard') }}">Admin</a>
      {% endif %}
      <a href="{{ url_for('logout') }}">Déconnexion</a>
    {% else %}
      <a href="{{ url_for('login') }}">Connexion</a>
      <a href="{{ url_for('register') }}">Inscription</a>
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
    {% block content %}{% endblock %}
  </main>
</body>
</html>

templates/index.html
{% extends "layout.html" %}
{% block content %}
<h1>Bienvenue</h1>
<p>Cette application permet de gérer les utilisateurs, leurs profils et un espace administrateur.</p>
{% endblock %}

templates/auth_register.html
{% extends "layout.html" %}
{% block content %}
<h2>Inscription</h2>
<form method="post">
  {{ form.hidden_tag() }}
  <div class="form-group">
    {{ form.name.label }} {{ form.name(size=32) }}
    {% for e in form.name.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.email.label }} {{ form.email(size=32) }}
    {% for e in form.email.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.password.label }} {{ form.password(size=32) }}
    {% for e in form.password.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.confirm.label }} {{ form.confirm(size=32) }}
    {% for e in form.confirm.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  {{ form.submit(class_="btn") }}
</form>
{% endblock %}

templates/auth_login.html
{% extends "layout.html" %}
{% block content %}
<h2>Connexion</h2>
<form method="post">
  {{ form.hidden_tag() }}
  <div class="form-group">
    {{ form.email.label }} {{ form.email(size=32) }}
    {% for e in form.email.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.password.label }} {{ form.password(size=32) }}
    {% for e in form.password.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.remember() }} {{ form.remember.label }}
  </div>
  {{ form.submit(class_="btn") }}
</form>
{% endblock %}

templates/profile.html
{% extends "layout.html" %}
{% block content %}
<h2>Mon profil</h2>
<div class="profile-card">
  {% if user.profile_image %}
    <img src="{{ url_for('uploaded_file', filename=user.profile_image) }}" class="avatar" alt="Photo de profil">
  {% else %}
    <div class="avatar placeholder">A</div>
  {% endif %}
  <div class="profile-info">
    <p><strong>Nom:</strong> {{ user.name }}</p>
    <p><strong>Email:</strong> {{ user.email }}</p>
    <p><strong>Bio:</strong> {{ user.bio or '-' }}</p>
    <p><strong>Rôle:</strong> {{ user.role }}</p>
    <p><strong>Statut:</strong> {{ 'Actif' if user.is_active else 'Désactivé' }}</p>
  </div>
</div>
<p><a class="btn" href="{{ url_for('profile_edit') }}">Modifier mon profil</a></p>
{% endblock %}

templates/profile_edit.html
{% extends "layout.html" %}
{% block content %}
<h2>Modifier mon profil</h2>
<form method="post" enctype="multipart/form-data">
  {{ form.hidden_tag() }}
  <div class="form-group">
    {{ form.name.label }} {{ form.name(size=40) }}
    {% for e in form.name.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.email.label }} {{ form.email(size=40) }}
    {% for e in form.email.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.bio.label }} {{ form.bio(rows=4, cols=60) }}
    {% for e in form.bio.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.profile_image.label }} {{ form.profile_image() }}
    <small>Max 5MB. Formats: png/jpg/jpeg/gif</small>
    {% for e in form.profile_image.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  {{ form.submit(class_="btn") }}
</form>
{% endblock %}

templates/admin_dashboard.html
{% extends "layout.html" %}
{% block content %}
<h2>Administration - Utilisateurs</h2>
<form method="get" class="search">
  <input type="text" name="q" value="{{ q }}" placeholder="Rechercher par nom ou email">
  <button class="btn" type="submit">Rechercher</button>
</form>
<table class="table">
  <thead>
    <tr>
      <th>ID</th><th>Nom</th><th>Email</th><th>Rôle</th><th>Actif</th><th>Créé</th><th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {% for u in users %}
    <tr>
      <td>{{ u.id }}</td>
      <td>{{ u.name }}</td>
      <td>{{ u.email }}</td>
      <td>{{ u.role }}</td>
      <td>{{ 'Oui' if u.is_active else 'Non' }}</td>
      <td>{{ u.created_at }}</td>
      <td>
        <a class="btn small" href="{{ url_for('admin_user_edit', user_id=u.id) }}">Modifier</a>
        <form method="post" action="{{ url_for('admin_user_toggle', user_id=u.id) }}" style="display:inline;">
          {{ csrf_token() }}
          <button class="btn small warn" type="submit">{{ 'Désactiver' if u.is_active else 'Activer' }}</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}

templates/admin_user_edit.html
{% extends "layout.html" %}
{% block content %}
<h2>Modifier l'utilisateur #{{ target.id }}</h2>
<form method="post">
  {{ form.hidden_tag() }}
  <div class="form-group">
    {{ form.name.label }} {{ form.name(size=40) }}
    {% for e in form.name.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.email.label }} {{ form.email(size=40) }}
    {% for e in form.email.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.bio.label }} {{ form.bio(rows=4, cols=60) }}
    {% for e in form.bio.errors %}<div class="error">{{ e }}</div>{% endfor %}
  </div>
  <div class="form-group">
    {{ form.role.label }} {{ form.role() }}
  </div>
  <div class="form-group">
    {{ form.is_active() }} {{ form.is_active.label }}
  </div>
  {{ form.submit(class_="btn") }}
</form>
{% endblock %}

static/style.css
body { font-family: Arial, sans-serif; margin: 0; background: #f7f7f7; color: #222; }
.container { max-width: 900px; margin: 20px auto; padding: 0 15px; }
.navbar { display: flex; gap: 10px; background: #333; color: #fff; padding: 10px 15px; }
.navbar a { color: #fff; text-decoration: none; }
h1, h2 { margin-top: 0; }
.form-group { margin-bottom: 12px; }
input[type=text], input[type=password], textarea { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
.btn { background: #0069d9; color: white; padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; }
.btn.small { padding: 4px 8px; font-size: 12px; }
.btn.warn { background: #d9534f; }
.table { width: 100%; border-collapse: collapse; background: white; }
.table th, .table td { border: 1px solid #ddd; padding: 8px; }
.flashes { list-style: none; padding: 0; }
.flash { padding: 8px; margin: 8px 0; border-radius: 4px; }
.flash.success { background: #d4edda; }
.flash.danger { background: #f8d7da; }
.flash.warning { background: #fff3cd; }
.flash.info { background: #cce5ff; }
.profile-card { display: flex; gap: 16px; background: white; padding: 16px; border-radius: 6px; }
.avatar { width: 96px; height: 96px; border-radius: 50%; object-fit: cover; }
.avatar.placeholder { width: 96px; height: 96px; border-radius: 50%; display: grid; place-items: center; background: #ddd; }

Notes de sécurité et production
- Changez SECRET_KEY via la variable d’environnement SECRET_KEY.
- Servez les fichiers statiques derrière un serveur web en production.
- Activez HTTPS, cookies Secure, et affinez les en-têtes (CSP).
- Ajoutez une limitation de taux et un verrouillage après échecs de connexion si nécessaire.
- Migrations: pour évoluer, envisagez Flask-Migrate + SQLAlchemy. Ici, SQLite + sqlite3 suffisent pour un POC.

C’est prêt à l’emploi. Dites-moi si vous souhaitez ajouter la réinitialisation de mot de passe, la suppression de compte, la pagination admin, ou une API JSON.