Voici une **application web Flask complète** permettant de gérer les utilisateurs :

---

### ✅ Fonctionnalités incluses :

- **Inscription** (email, mot de passe)
- **Connexion / Déconnexion**
- **Profil utilisateur** (nom, email, photo, bio)
- **Espace administrateur** (voir tous les utilisateurs, désactiver des comptes, changer les rôles)
- **Base de données SQLite**
- **Authentification sécurisée** (`bcrypt` pour les mots de passe)
- **Gestion des sessions**

---

### 📦 Dépendances à installer :

Avant de lancer l'application, installez les dépendances :

```bash
pip install flask flask_sqlalchemy flask_bcrypt flask_login pillow
```

---

## 📁 Structure du projet

```
user_management/
├── app.py
├── models.py
├── forms.py
├── requirements.txt
├── static/
│   └── uploads/         # Pour les photos de profil
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── profile.html
    ├── edit_profile.html
    ├── admin_dashboard.html
    └── admin_edit_user.html
```

---

## 📄 `app.py`

```python
from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
from forms import RegisterForm, LoginForm, EditProfileForm, AdminEditUserForm
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'une_cle_secrete'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            email=form.email.data,
            password=hashed_pw,
            name=form.name.data,
            role='user'
        )
        db.session.add(user)
        db.session.commit()
        flash("Inscription réussie !", "success")
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('profile'))
        flash("Email ou mot de passe incorrect", "danger")
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.bio = form.bio.data

        if form.profile_picture.data:
            file = form.profile_picture.data
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                current_user.profile_picture = filename
            else:
                flash("Format de fichier non autorisé", "danger")
                return render_template('edit_profile.html', form=form)

        db.session.commit()
        flash("Profil mis à jour !", "success")
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', form=form)

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    form = AdminEditUserForm(obj=user)
    if form.validate_on_submit():
        user.name = form.name.data
        user.email = form.email.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        db.session.commit()
        flash(f"Utilisateur {user.email} mis à jour", "success")
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_edit_user.html', form=form, user=user)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Créer un admin par défaut
        if not User.query.filter_by(email='admin@admin.com').first():
            admin = User(
                email='admin@admin.com',
                password=bcrypt.generate_password_hash('adminpassword').decode('utf-8'),
                name='Admin',
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
```

---

## 📄 `models.py`

```python
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    profile_picture = db.Column(db.String(200), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<User {self.email}>"
```

---

## 📄 `forms.py`

```python
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, BooleanField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class RegisterForm(FlaskForm):
    name = StringField('Nom', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(), EqualTo('password')
    ])

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])

class EditProfileForm(FlaskForm):
    name = StringField('Nom', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    bio = TextAreaField('Bio')
    profile_picture = FileField('Photo de profil')

class AdminEditUserForm(FlaskForm):
    name = StringField('Nom', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Rôle', choices=[('user', 'Utilisateur'), ('admin', 'Administrateur')])
    is_active = BooleanField('Actif')
```

---

## 📄 `templates/base.html`

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Gestion Utilisateurs</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">UserManager</a>
    <div class="navbar-nav ms-auto">
      {% if current_user.is_authenticated %}
        <a class="nav-link" href="/profile">Profil</a>
        {% if current_user.role == 'admin' %}
          <a class="nav-link" href="/admin">Admin</a>
        {% endif %}
        <a class="nav-link" href="/logout">Déconnexion</a>
      {% else %}
        <a class="nav-link" href="/login">Connexion</a>
        <a class="nav-link" href="/register">Inscription</a>
      {% endif %}
    </div>
  </div>
</nav>

<div class="container mt-4">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    {% block content %}{% endblock %}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

---

## 📄 `templates/index.html`

```html
{% extends "base.html" %}
{% block content %}
<h2>Bienvenue sur la plateforme</h2>
{% if current_user.is_authenticated %}
  <p>Bonjour, {{ current_user.name }} !</p>
{% else %}
  <p><a href="/login">Connectez-vous</a> ou <a href="/register">Inscrivez-vous</a>.</p>
{% endif %}
{% endblock %}
```

---

## 📄 `templates/register.html`

```html
{% extends "base.html" %}
{% block content %}
<h2>Inscription</h2>
<form method="POST">
    {{ form.hidden_tag() }}
    <div class="mb-3">
        {{ form.name.label(class="form-label") }}
        {{ form.name(class="form-control") }}
    </div>
    <div class="mb-3">
        {{ form.email.label(class="form-label") }}
        {{ form.email(class="form-control") }}
    </div>
    <div class="mb-3">
        {{ form.password.label(class="form-label") }}
        {{ form.password(class="form-control") }}
    </div>
    <div class="mb-3">
        {{ form.confirm_password.label(class="form-label") }}
        {{ form.confirm_password(class="form-control") }}
    </div>
    <button class="btn btn-primary">S'inscrire</button>
</form>
{% endblock %}
```

---

## 📄 `templates/login.html`

```html
{% extends "base.html" %}
{% block content %}
<h2>Connexion</h2>
<form method="POST">
    {{ form.hidden_tag() }}
    <div class="mb-3">
        {{ form.email.label(class="form-label") }}
        {{ form.email(class="form-control") }}
    </div>
    <div class="mb-3">
        {{ form.password.label(class="form-label") }}
        {{ form.password(class="form-control") }}
    </div>
    <button class="btn btn-primary">Se connecter</button>
</form>
{% endblock %}
```

---

## 📄 `templates/profile.html`

```html
{% extends "base.html" %}
{% block content %}
<h2>Profil</h2>
<p><strong>Nom :</strong> {{ current_user.name }}</p>
<p><strong>Email :</strong> {{ current_user.email }}</p>
<p><strong>Bio :</strong> {{ current_user.bio or 'Aucune bio' }}</p>
{% if current_user.profile_picture %}
<img src="/uploads/{{ current_user.profile_picture }}" alt="Photo de profil" width="100">
{% endif %}
<a href="/edit_profile" class="btn btn-primary">Modifier le profil</a>
{% endblock %}
```

---

## 📄 `templates/edit_profile.html`

```html
{% extends "base.html" %}
{% block content %}
<h2>Modifier le profil</h2>
<form method="POST" enctype="multipart/form-data">
    {{ form.hidden_tag() }}
    <div class="mb-3">
        {{ form.name.label(class="form-label") }}
        {{ form.name(class="form-control") }}
    </div>
    <div class="mb-3">
        {{ form.email.label(class="form-label") }}
        {{ form.email(class="form-control") }}
    </div>
    <div class="mb-3">
        {{ form.bio.label(class="form-label") }}
        {{ form.bio(class="form-control") }}
    </div>
    <div class="mb-3">
        {{ form.profile_picture.label(class="form-label") }}
        {{ form.profile_picture(class="form-control") }}
    </div>
    <button class="btn btn-primary">Enregistrer</button>
</form>
{% endblock %}
```

---

## 📄 `templates/admin_dashboard.html`

```html
{% extends "base.html" %}
{% block content %}
<h2>Administration</h2>
<table class="table table-striped">
    <thead>
        <tr>
            <th>Nom</th>
            <th>Email</th>
            <th>Rôle</th>
            <th>Actif</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for user in users %}
        <tr>
            <td>{{ user.name }}</td>
            <td>{{ user.email }}</td>
            <td>{{ user.role }}</td>
            <td>{{ 'Oui' if user.is_active else 'Non' }}</td>
            <td><a href="/admin/edit_user/{{ user.id }}" class="btn btn-sm btn-secondary">Modifier</a></td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

---

## 📄 `templates/admin_edit_user.html`

```html
{% extends "base.html" %}
{% block content %}
<h2>Modifier l'utilisateur</h2>
<form method="POST">
    {{ form.hidden_tag() }}
    <div class="mb-3">
        {{ form.name.label(class="form-label") }}
        {{ form.name(class="form-control") }}
    </div>
    <div class="mb-3">
        {{ form.email.label(class="form-label") }}
        {{ form.email(class="form-control") }}
    </div>
    <div class="mb-3">
        {{ form.role.label(class="form-label") }}
        {{ form.role(class="form-control") }}
    </div>
    <div class="mb-3 form-check">
        {{ form.is_active.label(class="form-check-label") }}
        {{ form.is_active(class="form-check-input") }}
    </div>
    <button class="btn btn-primary">Enregistrer</button>
</form>
{% endblock %}
```

---

## ✅ Lancer l'application

```bash
python app.py
```

Accédez à l’application via :  
👉 http://127.0.0.1:5000/

### 🔐 Compte administrateur par défaut :
- Email : `admin@admin.com`
- Mot de passe : `adminpassword`

---

Souhaitez-vous une version avec une API REST également ?