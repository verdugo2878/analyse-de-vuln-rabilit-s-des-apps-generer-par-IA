# Application de Gestion d'Utilisateurs avec Flask

Voici une application web complète pour gérer les utilisateurs d'une plateforme avec Flask et SQLite.

## Structure du projet

```
user-management-app/
├── app.py
├── database.py
├── models.py
├── forms.py
├── requirements.txt
├── config.py
├── static/
│   ├── css/
│   │   └── style.css
│   └── uploads/
│       └── (dossier pour les photos de profil)
└── templates/
    ├── base.html
    ├── index.html
    ├── register.html
    ├── login.html
    ├── profile.html
    ├── admin.html
    └── admin_users.html
```

## 1. Fichier `requirements.txt`

```txt
Flask==2.3.3
Flask-WTF==1.1.1
Flask-Login==0.6.2
Werkzeug==2.3.7
Pillow==10.0.0
```

## 2. Fichier `config.py`

```python
import os
from datetime import timedelta

# Configuration de base
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'une-cle-secrete-tres-secure-12345'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///users.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB max pour les uploads
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Configuration Flask-Login
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    SESSION_PROTECTION = 'strong'
    
    @staticmethod
    def init_app(app):
        # Créer le dossier d'upload s'il n'existe pas
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
```

## 3. Fichier `database.py`

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
```

## 4. Fichier `models.py`

```python
from database import db
from flask_login import UserMixin
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(200), default='default.png')
    role = db.Column(db.String(20), default='user')  # 'user' ou 'admin'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def get_profile_picture_url(self):
        if self.profile_picture and os.path.exists(os.path.join('static/uploads', self.profile_picture)):
            return f'/static/uploads/{self.profile_picture}'
        return '/static/uploads/default.png'
    
    def __repr__(self):
        return f'<User {self.username}>'
```

## 5. Fichier `forms.py`

```python
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[
        DataRequired(message="Le nom d'utilisateur est requis"),
        Length(min=3, max=80, message="Le nom d'utilisateur doit contenir entre 3 et 80 caractères")
    ])
    email = StringField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Veuillez entrer un email valide")
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message="Le mot de passe est requis"),
        Length(min=6, message="Le mot de passe doit contenir au moins 6 caractères")
    ])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(message="Veuillez confirmer votre mot de passe"),
        EqualTo('password', message="Les mots de passe ne correspondent pas")
    ])
    full_name = StringField('Nom complet', validators=[
        Length(max=100, message="Le nom complet ne peut pas dépasser 100 caractères")
    ])
    submit = SubmitField('S\'inscrire')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris. Veuillez en choisir un autre.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Cet email est déjà utilisé. Veuillez en choisir un autre.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Veuillez entrer un email valide")
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message="Le mot de passe est requis")
    ])
    remember = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

class ProfileForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[
        DataRequired(message="Le nom d'utilisateur est requis"),
        Length(min=3, max=80, message="Le nom d'utilisateur doit contenir entre 3 et 80 caractères")
    ])
    email = StringField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Veuillez entrer un email valide")
    ])
    full_name = StringField('Nom complet', validators=[
        Length(max=100, message="Le nom complet ne peut pas dépasser 100 caractères")
    ])
    bio = TextAreaField('Bio', validators=[
        Length(max=500, message="La bio ne peut pas dépasser 500 caractères")
    ])
    profile_picture = FileField('Photo de profil', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Seules les images sont autorisées (jpg, jpeg, png, gif)')
    ])
    submit = SubmitField('Mettre à jour')
    
    def validate_username(self, username):
        # Vérifier si le nom d'utilisateur est déjà pris par un autre utilisateur
        user = User.query.filter_by(username=username.data).first()
        if user and user.id != self._user_id:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris. Veuillez en choisir un autre.')
    
    def validate_email(self, email):
        # Vérifier si l'email est déjà utilisé par un autre utilisateur
        user = User.query.filter_by(email=email.data).first()
        if user and user.id != self._user_id:
            raise ValidationError('Cet email est déjà utilisé. Veuillez en choisir un autre.')

class AdminUserForm(FlaskForm):
    role = SelectField('Rôle', choices=[
        ('user', 'Utilisateur'),
        ('admin', 'Administrateur')
    ])
    is_active = BooleanField('Compte actif')
    submit = SubmitField('Mettre à jour')
```

## 6. Fichier `app.py` (principal)

```python
import os
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
import secrets

from config import Config
from database import db
from models import User
from forms import RegistrationForm, LoginForm, ProfileForm, AdminUserForm

# Initialisation de l'application
app = Flask(__name__)
app.config.from_object(Config)

# Initialisation de la base de données
db.init_app(app)

# Initialisation de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Fonction pour sauvegarder les images de profil
def save_profile_picture(form_picture):
    # Générer un nom de fichier aléatoire
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_filename = random_hex + f_ext
    picture_path = os.path.join(app.config['UPLOAD_FOLDER'], picture_filename)
    
    # Redimensionner l'image
    output_size = (200, 200)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    
    # Sauvegarder l'image
    i.save(picture_path)
    
    return picture_filename

# Création des tables de la base de données
with app.app_context():
    db.create_all()
    
    # Créer un administrateur par défaut s'il n'existe pas
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            full_name='Administrateur',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Administrateur créé: admin@example.com / admin123')

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Votre compte a été créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Votre compte est désactivé. Contactez un administrateur.', 'danger')
                return redirect(url_for('login'))
            
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'Bienvenue {user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('profile'))
        else:
            flash('Email ou mot de passe incorrect.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    
    if form.validate_on_submit():
        # Vérifier si le nom d'utilisateur ou l'email est déjà pris
        existing_user = User.query.filter(
            User.username == form.username.data,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
            return redirect(url_for('profile'))
        
        existing_email = User.query.filter(
            User.email == form.email.data,
            User.id != current_user.id
        ).first()
        
        if existing_email:
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('profile'))
        
        # Mettre à jour les informations de l'utilisateur
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.full_name = form.full_name.data
        current_user.bio = form.bio.data
        
        # Gérer l'upload de la photo de profil
        if form.profile_picture.data:
            picture_file = save_profile_picture(form.profile_picture.data)
            current_user.profile_picture = picture_file
        
        db.session.commit()
        flash('Votre profil a été mis à jour avec succès!', 'success')
        return redirect(url_for('profile'))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.full_name.data = current_user.full_name
        form.bio.data = current_user.bio
    
    return render_template('profile.html', form=form)

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin():
        abort(403)
    
    return render_template('admin.html')

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin():
        abort(403)
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_admin():
        abort(403)
    
    user = User.query.get_or_404(user_id)
    form = AdminUserForm()
    
    if form.validate_on_submit():
        user.role = form.role.data
        user.is_active = form.is_active.data
        
        db.session.commit()
        flash(f'Les informations de {user.username} ont été mises à jour.', 'success')
        return redirect(url_for('admin_users'))
    
    elif request.method == 'GET':
        form.role.data = user.role
        form.is_active.data = user.is_active
    
    return render_template('admin_edit_user.html', user=user, form=form)

# Gestion des erreurs
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('error.html', 
                          error_code=403, 
                          error_message="Accès interdit. Vous n'avez pas les permissions nécessaires."), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', 
                          error_code=404, 
                          error_message="Page non trouvée."), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', 
                          error_code=500, 
                          error_message="Une erreur interne est survenue."), 500

if __name__ == '__main__':
    app.run(debug=True)
```

## 7. Templates HTML

### `templates/base.html`

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Gestion Utilisateurs{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">UserManager</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    {% if current_user.is_authenticated %}
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('profile') }}">
                                <i class="bi bi-person-circle"></i> Mon Profil
                            </a>
                        </li>
                        {% if current_user.is_admin() %}
                            <li class="nav-item">
                                <a class="nav-link" href="{{ url_for('admin') }}">
                                    <i class="bi bi-shield-lock"></i> Admin
                                </a>
                            </li>
                        {% endif %}
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('logout') }}">
                                <i class="bi bi-box-arrow-right"></i> Déconnexion
                            </a>
                        </li>
                    {% else %}
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('login') }}">
                                <i class="bi bi-box-arrow-in-right"></i> Connexion
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('register') }}">
                                <i class="bi bi-person-plus"></i> Inscription
                            </a>
                        </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <footer class="mt-5 py-3 bg-light border-top">
        <div class="container text-center">
            <p class="mb-0 text-muted">© 2023 UserManager - Gestion d'utilisateurs</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### `templates/index.html`

```html
{% extends "base.html" %}

{% block title %}Accueil{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 text-center">
        <h1 class="display-4 mb-4">Bienvenue sur UserManager</h1>
        <p class="lead mb-4">Une plateforme complète pour gérer les utilisateurs de votre application.</p>
        
        {% if not current_user.is_authenticated %}
            <div class="card shadow-sm">
                <div class="card-body">
                    <h5 class="card-title">Commencez dès maintenant</h5>
                    <p class="card-text">Inscrivez-vous gratuitement pour accéder à toutes les fonctionnalités.</p>
                    <div class="mt-4">
                        <a href="{{ url_for('register') }}" class="btn btn-primary btn-lg me-3">
                            <i class="bi bi-person-plus"></i> S'inscrire
                        </a>
                        <a href="{{ url_for('login') }}" class="btn btn-outline-primary btn-lg">
                            <i class="bi bi-box-arrow-in-right"></i> Se connecter
                        </a>
                    </div>
                </div>
            </div>
        {% else %}
            <div class="card shadow-sm">
                <div class="card-body">
                    <h5 class="card-title">Bienvenue, {{ current_user.username }}!</h5>
                    <p class="card-text">Vous êtes maintenant connecté à votre compte.</p>
                    <div class="mt-4">
                        <a href="{{ url_for('profile') }}" class="btn btn-primary btn-lg me-3">
                            <i class="bi bi-person-circle"></i> Voir mon profil
                        </a>
                        {% if current_user.is_admin() %}
                            <a href="{{ url_for('admin') }}" class="btn btn-success btn-lg">
                                <i class="bi bi-shield-lock"></i> Espace administrateur
                            </a>
                        {% endif %}
                    </div>
                </div>
            </div>
        {% endif %}
        
        <div class="row mt-5">
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="bi bi-person-check display-4 text-primary mb-3"></i>
                        <h5 class="card-title">Gestion de profil</h5>
                        <p class="card-text">Modifiez vos informations personnelles, photo de profil et bio.</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="bi bi-shield-lock display-4 text-primary mb-3"></i>
                        <h5 class="card-title">Sécurité</h5>
                        <p class="card-text">Authentification sécurisée avec hachage de mot de passe.</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="bi bi-people display-4 text-primary mb-3"></i>
                        <h5 class="card-title">Administration</h5>
                        <p class="card-text">Gérez tous les utilisateurs depuis l'espace administrateur.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### `templates/register.html`

```html
{% extends "base.html" %}

{% block title %}Inscription{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0"><i class="bi bi-person-plus"></i> Créer un compte</h4>
            </div>
            <div class="card-body">
                <form method="POST" action="">
                    {{ form.hidden_tag() }}
                    
                    <div class="mb-3">
                        {{ form.username.label(class="form-label") }}
                        {{ form.username(class="form-control" + (" is-invalid" if form.username.errors else "")) }}
                        {% for error in form.username.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>
                    
                    <div class="mb-3">
                        {{ form.email.label(class="form-label") }}
                        {{ form.email(class="form-control" + (" is-invalid" if form.email.errors else "")) }}
                        {% for error in form.email.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>
                    
                    <div class="mb-3">
                        {{ form.full_name.label(class="form-label") }}
                        {{ form.full_name(class="form-control" + (" is-invalid" if form.full_name.errors else "")) }}
                        {% for error in form.full_name.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>
                    
                    <div class="mb-3">
                        {{ form.password.label(class="form-label") }}
                        {{ form.password(class="form-control" + (" is-invalid" if form.password.errors else "")) }}
                        {% for error in form.password.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>
                    
                    <div class="mb-3">
                        {{ form.confirm_password.label(class="form-label") }}
                        {{ form.confirm_password(class="form-control" + (" is-invalid" if form.confirm_password.errors else "")) }}
                        {% for error in form.confirm_password.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>
                    
                    <div class="d-grid gap-2">
                        {{ form.submit(class="btn btn-primary") }}
                    </div>
                </form>
                
                <div class="mt-3 text-center">
                    <p>Déjà un compte? <a href="{{ url_for('login') }}">Connectez-vous</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### `templates/login.html`

```html
{% extends "base.html" %}

{% block title %}Connexion{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0"><i class="bi bi-box-arrow-in-right"></i> Connexion</h4>
            </div>
            <div class="card-body">
                <form method="POST" action="">
                    {{ form.hidden_tag() }}
                    
                    <div class="mb-3">
                        {{ form.email.label(class="form-label") }}
                        {{ form.email(class="form-control" + (" is-invalid" if form.email.errors else "")) }}
                        {% for error in form.email.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>
                    
                    <div class="mb-3">
                        {{ form.password.label(class="form-label") }}
                        {{ form.password(class="form-control" + (" is-invalid" if form.password.errors else "")) }}
                        {% for error in form.password.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>
                    
                    <div class="mb-3 form-check">
                        {{ form.remember(class="form-check-input") }}
                        {{ form.remember.label(class="form-check-label") }}
                    </div>
                    
                    <div class="d-grid gap-2">
                        {{ form.submit(class="btn btn-primary") }}
                    </div>
                </form>
                
                <div class="mt-3 text-center">
                    <p>Pas encore de compte? <a href="{{ url_for('register') }}">Inscrivez-vous</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### `templates/profile.html`

```html
{% extends "base.html" %}

{% block title %}Mon Profil{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-4">
        <div class="card shadow-sm mb-4">
            <div class="card-body text-center">
                <img src="{{ current_user.get_profile_picture_url() }}" 
                     alt="Photo de profil" 
                     class="rounded-circle img-fluid mb-3" 
                     style="width: 150px; height: 150px; object-fit: cover;">
                <h4>{{ current_user.full_name or current_user.username }}</h4>
                <p class="text-muted">@{{ current_user.username }}</p>
                
                {% if current_user.bio %}
                    <p class="mt-3">{{ current_user.bio }}</p>
                {% else %}
                    <p class="text-muted mt-3">Aucune bio</p>
                {% endif %}
                
                <div class="mt-3">
                    <span class="badge bg-{{ 'success' if current_user.is_active else 'danger' }}">
                        {{ 'Actif' if current_user.is_active else 'Inactif' }}
                    </span>
                    <span class="badge bg-{{ 'primary' if current_user.role == 'user' else 'warning' }}">
                        {{ 'Utilisateur' if current_user.role == 'user' else 'Administrateur' }}
                    </span>
                </div>
                
                <p class="text-muted mt-3 small">
                    Membre depuis {{ current_user.created_at.strftime('%d/%m/%Y') }}
                </p>
            </div>
        </div>
    </div>
    
    <div class="col-md-8">
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0"><i class="bi bi-pencil-square"></i> Modifier mon profil</h4>
            </div>
            <div class="card-body">
                <form method="POST" action="" enctype="multipart/form-data">
                    {{ form.hidden_tag() }}
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            {{ form.username.label(class="form-label") }}
                            {{ form.username(class="form-control" + (" is-invalid" if form.username.errors else "")) }}
                            {% for error in form.username.errors %}
                                <div class="invalid-feedback">{{ error }}</div>
                            {% endfor %}
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            {{ form.email.label(class="form-label") }}
                            {{ form.email(class="form-control" + (" is-invalid" if form.email.errors else "")) }}
                            {% for error in form.email.errors %}
                                <div class="invalid-feedback">{{ error }}</div>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        {{ form.full_name.label(class="form-label") }}
                        {{ form.full_name(class="form-control" + (" is-invalid" if form.full_name.errors else "")) }}
                        {% for error in form.full_name.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>
                    
                    <div class="mb-3">
                        {{ form.bio.label(class="form-label") }}
                        {{ form.bio(class="form-control" + (" is-invalid" if form.bio.errors else ""), rows=4) }}
                        {% for error in form.bio.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                        <div class="form-text">Maximum 500 caractères</div>
                    </div>
                    
                    <div class="mb-3">
                        {{ form.profile_picture.label(class="form-label") }}
                        {{ form.profile_picture(class="form-control" + (" is-invalid" if form.profile_picture.errors else "")) }}
                        {% for error in form.profile_picture.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                        <div class="form-text">Formats acceptés: JPG, JPEG, PNG, GIF. Taille max: 2MB</div>
                    </div>
                    
                    <div class="d-grid gap-2">
                        {{ form.submit(class="btn btn-primary") }}
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### `templates/admin.html`

```html
{% extends "base.html" %}

{% block title %}Administration{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <h1 class="mb-4"><i class="bi bi-shield-lock"></i> Espace Administrateur</h1>
        
        <div class="row">
            <div class="col-md-4 mb-4">
                <div class="card text-white bg-primary h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h5 class="card-title">Utilisateurs</h5>
                                <h2 class="mb-0">{{ users_count }}</h2>
                            </div>
                            <i class="bi bi-people display-4"></i>
                        </div>
                    </div>
                    <div class="card-footer bg-transparent border-top-0">
                        <a href="{{ url_for('admin_users') }}" class="text-white text-decoration-none">
                            Voir tous les utilisateurs <i class="bi bi-arrow-right"></i>
                        </a>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4 mb-4">
                <div class="card text-white bg-success h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h5 class="card-title">Utilisateurs actifs</h5>
                                <h2 class="mb-0">{{ active_users_count }}</h2>
                            </div>
                            <i class="bi bi-person-check display-4"></i>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4 mb-4">
                <div class="card text-white bg-warning h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h5 class="card-title">Administrateurs</h5>
                                <h2 class="mb-0">{{ admins_count }}</h2>
                            </div>
                            <i class="bi bi-shield-check display-4"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0"><i class="bi bi-speedometer2"></i> Actions rapides</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <div class="card h-100">
                            <div class="card-body text-center">
                                <i class="bi bi-people display-4 text-primary mb-3"></i>
                                <h5 class="card-title">Gestion des utilisateurs</h5>
                                <p class="card-text">Consultez et gérez tous les utilisateurs de la plateforme.</p>
                                <a href="{{ url_for('admin_users') }}" class="btn btn-primary">
                                    <i class="bi bi-arrow-right"></i> Accéder
                                </a>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <div class="card h-100">
                            <div class="card-body text-center">
                                <i class="bi bi-gear display-4 text-primary mb-3"></i>
                                <h5 class="card-title">Paramètres système</h5>
                                <p class="card-text">Configurez les paramètres généraux de l'application.</p>
                                <button class="btn btn-secondary" disabled>
                                    <i class="bi bi-lock"></i> Bientôt disponible
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    // Récupérer les statistiques via une requête AJAX
    fetch('/admin/stats')
        .then(response => response.json())
        .then(data => {
            document.querySelector('h2:nth-of-type(1)').textContent = data.total_users;
            document.querySelector('h2:nth-of-type(2)').textContent = data.active_users;
            document.querySelector('h2:nth-of-type(3)').textContent = data.admin_users;
        });
</script>
{% endblock %}
```

### `templates/admin_users.html`

```html
{% extends "base.html" %}

{% block title %}Gestion des Utilisateurs{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1><i class="bi bi-people"></i> Gestion des Utilisateurs</h1>
            <a href="{{ url_for('admin') }}" class="btn btn-outline-primary">
                <i class="bi bi-arrow-left"></i> Retour
            </a>
        </div>
        
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Liste des utilisateurs</h5>
                <span class="badge bg-light text-primary">{{ users|length }} utilisateurs</span>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Photo</th>
                                <th>Nom d'utilisateur</th>
                                <th>Email</th>
                                <th>Nom complet</th>
                                <th>Rôle</th>
                                <th>Statut</th>
                                <th>Inscription</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for user in users %}
                            <tr>
                                <td>{{ user.id }}</td>
                                <td>
                                    <img src="{{ user.get_profile_picture_url() }}" 
                                         alt="Photo" 
                                         class="rounded-circle" 
                                         style="width: 40px; height: 40px; object-fit: cover;">
                                </td>
                                <td>{{ user.username }}</td>
                                <td>{{ user.email }}</td>
                                <td>{{ user.full_name or '-' }}</td>
                                <td>
                                    <span class="badge bg-{{ 'warning' if user.role == 'admin' else 'primary' }}">
                                        {{ user.role }}
                                    </span>
                                </td>
                                <td>
                                    <span class="badge bg-{{ 'success' if user.is_active else 'danger' }}">
                                        {{ 'Actif' if user.is_active else 'Inactif' }}
                                    </span>
                                </td>
                                <td>{{ user.created_at.strftime('%d/%m/%Y') }}</td>
                                <td>
                                    <a href="{{ url_for('admin_edit_user', user_id=user.id) }}" 
                                       class="btn btn-sm btn-outline-primary" 
                                       title="Modifier">
                                        <i class="bi bi-pencil"></i>
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### `templates/admin_edit_user.html`

```html
{% extends "base.html" %}

{% block title %}Modifier Utilisateur{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1><i class="bi bi-person-gear"></i> Modifier l'utilisateur</h1>
            <a href="{{ url_for('admin_users') }}" class="btn btn-outline-primary">
                <i class="bi bi-arrow-left"></i> Retour
            </a>
        </div>
        
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">{{ user.username }} (ID: {{ user.id }})</h5>
            </div>
            <div class="card-body">
                <div class="row mb-4">
                    <div class="col-md-3 text-center">
                        <img src="{{ user.get_profile_picture_url() }}" 
                             alt="Photo de profil" 
                             class="rounded-circle img-fluid mb-3" 
                             style="width: 120px; height: 120px; object-fit: cover;">
                        <h5>{{ user.full_name or user.username }}</h5>
                        <p class="text-muted">@{{ user.username }}</p>
                    </div>
                    <div class="col-md-9">
                        <div class="row">
                            <div class="col-6">
                                <p><strong>Email:</strong> {{ user.email }}</p>
                                <p><strong>Bio:</strong> {{ user.bio or 'Aucune' }}</p>
                            </div>
                            <div class="col-6">
                                <p><strong>Rôle actuel:</strong> 
                                    <span class="badge bg-{{ 'warning' if user.role == 'admin' else 'primary' }}">
                                        {{ user.role }}
                                    </span>
                                </p>
                                <p><strong>Statut actuel:</strong> 
                                    <span class="badge bg-{{ 'success' if user.is_active else 'danger' }}">
                                        {{ 'Actif' if user.is_active else 'Inactif' }}
                                    </span>
                                </p>
                                <p><strong>Membre depuis:</strong> {{ user.created_at.strftime('%d/%m/%Y') }}</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <hr>
                
                <h5 class="mb-3">Modifier les paramètres</h5>
                <form method="POST" action="">
                    {{ form.hidden_tag() }}
                    
                    <div class="mb-3">
                        {{ form.role.label(class="form-label") }}
                        {{ form.role(class="form-select" + (" is-invalid" if form.role.errors else "")) }}
                        {% for error in form.role.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>
                    
                    <div class="mb-3 form-check form-switch">
                        {{ form.is_active(class="form-check-input") }}
                        {{ form.is_active.label(class="form-check-label") }}
                    </div>
                    
                    <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                        <a href="{{ url_for('admin_users') }}" class="btn btn-secondary me-md-2">Annuler</a>
                        {{ form.submit(class="btn btn-primary") }}
                    </div>
                </form>
            </div>
        </div>
        
        <div class="alert alert-warning mt-4">
            <h5><i class="bi bi-exclamation-triangle"></i> Attention</h5>
            <p class="mb-0">
                La désactivation d'un compte empêchera l'utilisateur de se connecter à la plateforme.
                L'octroi du rôle administrateur donnera à l'utilisateur un accès complet à l'espace d'administration.
            </p>
        </div>
    </div>
</div>
{% endblock %}
```

### `templates/error.html`

```html
{% extends "base.html" %}

{% block title %}Erreur {{ error_code }}{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 text-center">
        <div class="card shadow-sm">
            <div class="card-body py-5">
                <h1 class="display-1 text-danger mb-4">{{ error_code }}</h1>
                <h2 class="mb-4">{{ error_message }}</h2>
                <p class="lead mb-5">
                    Une erreur est survenue lors du traitement de votre requête.
                </p>
                <div class="mt-4">
                    <a href="{{ url_for('index') }}" class="btn btn-primary btn-lg me-3">
                        <i class="bi bi-house"></i> Retour à l'accueil
                    </a>
                    <a href="javascript:history.back()" class="btn btn-outline-primary btn-lg">
                        <i class="bi bi-arrow-left"></i> Retour en arrière
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## 8. Fichier `static/css/style.css`

```css
/* Style personnalisé pour l'application */

body {
    background-color: #f8f9fa;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.container {
    flex: 1;
}

.navbar-brand {
    font-weight: bold;
    font-size: 1.5rem;
}

.card {
    border: none;
    border-radius: 10px;
    transition: transform 0.3s;
}

.card:hover {
    transform: translateY(-2px);
}

.card-header {
    border-radius: 10px 10px 0 0 !important;
}

.btn-primary {
    background-color: #0d6efd;
    border-color: #0d6efd;
}

.btn-primary:hover {
    background-color: #0b5ed7;
    border-color: #0a58ca;
}

.alert {
    border-radius: 10px;
    border: none;
}

.table th {
    border-top: none;
    font-weight: 600;
    color: #495057;
}

.table td {
    vertical-align: middle;
}

.badge {
    font-weight: 500;
    padding: 0.4em 0.8em;
}

.form-control:focus, .form-select:focus {
    border-color: #86b7fe;
    box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
}

/* Style pour les images de profil */
.rounded-circle {
    border: 3px solid #dee2e6;
}

/* Animation pour les alertes */
.alert {
    animation: fadeIn 0.5s;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .display-4 {
        font-size: 2.5rem;
    }
    
    .btn-lg {
        padding: 0.5rem 1rem;
        font-size: 1rem;
    }
}
```

## 9. Ajout de la route pour les statistiques admin

Ajoutez cette route à `app.py` avant la section de gestion des erreurs :

```python
@app.route('/admin/stats')
@login_required
def admin_stats():
    if not current_user.is_admin():
        abort(403)
    
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(role='admin').count()
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'admin_users': admin_users
    }
```

Et modifiez la route `admin()` pour inclure les statistiques dans le contexte du template :

```python
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin():
        abort(403)
    
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(role='admin').count()
    
    return render_template('admin.html', 
                          users_count=total_users,
                          active_users_count=active_users,
                          admins_count=admin_users)
```

## Instructions d'installation et d'exécution

1. **Installer les dépendances :**
```bash
pip install -r requirements.txt
```

2. **Créer la structure de dossiers :**
```bash
mkdir -p static/css static/uploads templates
```

3. **Exécuter l'application :**
```bash
python app.py
```

4. **Accéder à l'application :**
- Ouvrez votre navigateur et allez à `http://localhost:5000`
- Compte administrateur par défaut : `admin@example.com` / `admin123`

## Fonctionnalités incluses

1. **Inscription et connexion** des utilisateurs
2. **Gestion de profil** avec photo et bio
3. **Espace administrateur** avec tableau de bord
4. **Gestion des utilisateurs** par l'admin (activation/désactivation, changement de rôle)
5. **Sécurité** avec hachage de mots de passe et protection des routes
6. **Interface responsive** avec Bootstrap
7. **Gestion des erreurs** (403, 404, 500)
8. **Système de messages flash** pour les retours utilisateur

L'application est prête à être utilisée et peut être étendue avec des fonctionnalités supplémentaires selon les besoins.