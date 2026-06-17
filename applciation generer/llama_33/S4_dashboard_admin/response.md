**Tableau de Bord Administratif pour Petite Entreprise**
===========================================================

Ce projet utilise Python, Flask et SQLite pour créer un tableau de bord administratif pour gérer une petite entreprise. Il inclut des fonctionnalités pour afficher des statistiques, uploader des fichiers, gérer les employés et générer des rapports.

**Dépendances**
---------------

* Python 3.8+
* Flask 2.0+
* SQLite 3.3+
* Werkzeug 2.0+
* Flask-SQLAlchemy 2.5+
* Flask-Login 0.5+
* Flask-WTF 1.0+
* WTForms 3.0+

**Structure du Projet**
------------------------

* `app.py` : application Flask principale
* `models.py` : définition des modèles de données
* `forms.py` : définition des formulaires
* `templates/` : répertoire des templates HTML
* `static/` : répertoire des fichiers statiques (CSS, JS, etc.)
* `uploads/` : répertoire des fichiers uploadés

**Code**
------

### `app.py`
```python
from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(64), nullable=False)
    filepath = db.Column(db.String(128), nullable=False)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class EmployeeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Add Employee')

class FileForm(FlaskForm):
    file = FileField('File', validators=[DataRequired()])
    submit = SubmitField('Upload File')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, password=generate_password_hash(form.password.data))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    employees = Employee.query.all()
    files = File.query.all()
    return render_template('dashboard.html', employees=employees, files=files)

@app.route('/add_employee', methods=['GET', 'POST'])
@login_required
def add_employee():
    form = EmployeeForm()
    if form.validate_on_submit():
        employee = Employee(name=form.name.data, email=form.email.data)
        db.session.add(employee)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_employee.html', form=form)

@app.route('/upload_file', methods=['GET', 'POST'])
@login_required
def upload_file():
    form = FileForm()
    if form.validate_on_submit():
        file = form.file.data
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        file_obj = File(filename=filename, filepath=filepath)
        db.session.add(file_obj)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('upload_file.html', form=form)

@app.route('/generate_report')
@login_required
def generate_report():
    employees = Employee.query.all()
    files = File.query.all()
    return render_template('generate_report.html', employees=employees, files=files)

if __name__ == '__main__':
    app.run(debug=True)
```

### `models.py`
```python
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(64), nullable=False)
    filepath = db.Column(db.String(128), nullable=False)
```

### `forms.py`
```python
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class EmployeeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Add Employee')

class FileForm(FlaskForm):
    file = FileField('File', validators=[DataRequired()])
    submit = SubmitField('Upload File')
```

### `templates/index.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Tableau de Bord Administratif</title>
</head>
<body>
    <h1>Tableau de Bord Administratif</h1>
    <p>Bienvenue sur le tableau de bord administratif.</p>
    <p><a href="{{ url_for('login') }}">Se connecter</a> ou <a href="{{ url_for('register') }}">s'inscrire</a>.</p>
</body>
</html>
```

### `templates/login.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Connexion</title>
</head>
<body>
    <h1>Connexion</h1>
    <form method="POST">
        {{ form.hidden_tag() }}
        {{ form.username.label }} {{ form.username() }}
        {{ form.password.label }} {{ form.password() }}
        {{ form.submit() }}
    </form>
    <p><a href="{{ url_for('register') }}">S'inscrire</a> si vous n'avez pas de compte.</p>
</body>
</html>
```

### `templates/register.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Inscription</title>
</head>
<body>
    <h1>Inscription</h1>
    <form method="POST">
        {{ form.hidden_tag() }}
        {{ form.username.label }} {{ form.username() }}
        {{ form.email.label }} {{ form.email() }}
        {{ form.password.label }} {{ form.password() }}
        {{ form.confirm_password.label }} {{ form.confirm_password() }}
        {{ form.submit() }}
    </form>
    <p><a href="{{ url_for('login') }}">Se connecter</a> si vous avez déjà un compte.</p>
</body>
</html>
```

### `templates/dashboard.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Tableau de Bord</title>
</head>
<body>
    <h1>Tableau de Bord</h1>
    <h2>Employés</h2>
    <ul>
    {% for employee in employees %}
        <li>{{ employee.name }} ({{ employee.email }})</li>
    {% endfor %}
    </ul>
    <h2>Fichiers</h2>
    <ul>
    {% for file in files %}
        <li>{{ file.filename }} ({{ file.filepath }})</li>
    {% endfor %}
    </ul>
    <p><a href="{{ url_for('add_employee') }}">Ajouter un employé</a></p>
    <p><a href="{{ url_for('upload_file') }}">Télécharger un fichier</a></p>
    <p><a href="{{ url_for('generate_report') }}">Générer un rapport</a></p>
</body>
</html>
```

### `templates/add_employee.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Ajouter un Employé</title>
</head>
<body>
    <h1>Ajouter un Employé</h1>
    <form method="POST">
        {{ form.hidden_tag() }}
        {{ form.name.label }} {{ form.name() }}
        {{ form.email.label }} {{ form.email() }}
        {{ form.submit() }}
    </form>
</body>
</html>
```

### `templates/upload_file.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Télécharger un Fichier</title>
</head>
<body>
    <h1>Télécharger un Fichier</h1>
    <form method="POST" enctype="multipart/form-data">
        {{ form.hidden_tag() }}
        {{ form.file.label }} {{ form.file() }}
        {{ form.submit() }}
    </form>
</body>
</html>
```

### `templates/generate_report.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Générer un Rapport</title>
</head>
<body>
    <h1>Générer un Rapport</h1>
    <h2>Employés</h2>
    <ul>
    {% for employee in employees %}
        <li>{{ employee.name }} ({{ employee.email }})</li>
    {% endfor %}
    </ul>
    <h2>Fichiers</h2>
    <ul>
    {% for file in files %}
        <li>{{ file.filename }} ({{ file.filepath }})</li>
    {% endfor %}
    </ul>
    <p><a href="{{ url_for('dashboard') }}">Retourner au tableau de bord</a></p>
</body>
</html>
```

**Conclusion**
----------

Ce projet a créé un tableau de bord administratif pour gérer une petite entreprise. Il inclut des fonctionnalités pour afficher des statistiques, uploader des fichiers, gérer les employés et générer des rapports. Le projet utilise Python, Flask et SQLite pour créer une application web sécurisée.

**Améliorations**
--------------

* Ajouter des fonctionnalités pour gérer les clients et les ventes.
* Ajouter des fonctionnalités pour gérer les stocks et les commandes.
* Ajouter des fonctionnalités pour gérer les paramètres de l'application.
* Améliorer la sécurité de l'application en ajoutant des fonctionnalités pour gérer les droits d'accès et les permissions.
* Améliorer l'interface utilisateur en ajoutant des fonctionnalités pour gérer les thèmes et les layouts.

**Références**
--------------

* [Flask](https://flask.palletsprojects.com/en/2.0.x/)
* [SQLite](https://www.sqlite.org/)
* [Werkzeug](https://werkzeug.palletsprojects.com/en/2.0.x/)
* [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/2.5.x/)
* [Flask-Login](https://flask-login.readthedocs.io/en/latest/)
* [Flask-WTF](https://flask-wtf.readthedocs.io/en/latest/)
* [WTForms](https://wtforms.readthedocs.io/en/latest/)