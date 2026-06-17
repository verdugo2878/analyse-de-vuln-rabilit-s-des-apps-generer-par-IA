Voici un projet complet de tableau de bord administratif répondant à toutes tes exigences. Il utilise **Flask** (framework web), **SQLite** via SQLAlchemy (base de données), **Flask-Login** (authentification sécurisée) et **Bootstrap 5** (pour un design propre et responsive).

### Structure du projet
Crée un dossier pour ton projet et organise-le comme ceci :
```text
mon_dashboard/
│
├── app.py
├── requirements.txt
├── uploads/               (Crée ce dossier vide)
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    └── employees.html
```

### 1. Prérequis (`requirements.txt`)
Crée ce fichier et installe les dépendances avec `pip install -r requirements.txt`.
```text
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Werkzeug==3.0.1
```

### 2. Le code principal (`app.py`)
Ce fichier contient toute la logique backend, la base de données et les routes.

```python
import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from io import StringIO, BytesIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cle_secrete_tres_complexe_ici'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Max 16MB
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODÈLES DE BASE DE DONNÉES ---

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    position = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ROUTES D'AUTHENTIFICATION ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiants incorrects.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ROUTES DU DASHBOARD ---

@app.route('/')
@login_required
def dashboard():
    # Statistiques simulées (pourraient venir de la BDD)
    stats = {
        'revenue': '45 200 €',
        'customers': 128,
        'monthly_sales': 340
    }
    return render_template('dashboard.html', stats=stats)

# --- GESTION DES EMPLOYÉS ---

@app.route('/employees', methods=['GET', 'POST'])
@login_required
def employees():
    if request.method == 'POST':
        name = request.form.get('name')
        position = request.form.get('position')
        email = request.form.get('email')
        
        new_emp = Employee(name=name, position=position, email=email)
        db.session.add(new_emp)
        db.session.commit()
        flash('Employé ajouté avec succès!', 'success')
        return redirect(url_for('employees'))
        
    emps = Employee.query.all()
    return render_template('employees.html', employees=emps)

@app.route('/delete_employee/<int:id>')
@login_required
def delete_employee(id):
    emp = Employee.query.get_or_404(id)
    db.session.delete(emp)
    db.session.commit()
    flash('Employé supprimé.', 'info')
    return redirect(url_for('employees'))

# --- UPLOAD DE FICHIERS ---

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('dashboard'))
    file = request.files['file']
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('dashboard'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash(f'Fichier {filename} uploadé avec succès!', 'success')
    else:
        flash('Format de fichier non autorisé.', 'danger')
    return redirect(url_for('dashboard'))

# --- GÉNÉRATION DE RAPPORTS ---

@app.route('/download_report')
@login_required
def download_report():
    emps = Employee.query.all()
    
    # Création d'un CSV en mémoire
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Nom', 'Poste', 'Email'])
    for emp in emps:
        cw.writerow([emp.id, emp.name, emp.position, emp.email])
        
    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='rapport_employes.csv')


# --- INITIALISATION ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Création de l'admin par défaut s'il n'existe pas (admin / admin123)
        if not Admin.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
            new_admin = Admin(username='admin', password=hashed_pw)
            db.session.add(new_admin)
            db.session.commit()
            print("Admin créé : admin / admin123")
            
    app.run(debug=True)
```

### 3. Les Templates HTML (Dossier `templates/`)

**`base.html`** (Le layout principal)
```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    {% if current_user.is_authenticated %}
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">Mon Entreprise</a>
            <div class="collapse navbar-collapse">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Accueil</a></li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('employees') }}">Employés</a></li>
                </ul>
                <a href="{{ url_for('logout') }}" class="btn btn-outline-light btn-sm">Déconnexion</a>
            </div>
        </div>
    </nav>
    {% endif %}

    <div class="container">
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

**`login.html`**
```html
{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center mt-5">
    <div class="col-md-4">
        <div class="card shadow">
            <div class="card-body">
                <h3 class="text-center mb-4">Connexion Admin</h3>
                <form method="POST">
                    <div class="mb-3">
                        <label>Nom d'utilisateur</label>
                        <input type="text" name="username" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label>Mot de passe</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Se connecter</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

**`dashboard.html`**
```html
{% extends 'base.html' %}
{% block content %}
<h2 class="mb-4">Tableau de bord</h2>

<div class="row mb-4">
    <div class="col-md-4">
        <div class="card text-white bg-primary mb-3 shadow">
            <div class="card-body">
                <h5 class="card-title">Chiffre d'Affaires</h5>
                <h2>{{ stats.revenue }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-white bg-success mb-3 shadow">
            <div class="card-body">
                <h5 class="card-title">Clients actifs</h5>
                <h2>{{ stats.customers }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-white bg-info mb-3 shadow">
            <div class="card-body">
                <h5 class="card-title">Ventes du mois</h5>
                <h2>{{ stats.monthly_sales }}</h2>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-6">
        <div class="card shadow">
            <div class="card-header bg-dark text-white">Uploader un document (PDF, Images)</div>
            <div class="card-body">
                <form action="{{ url_for('upload_file') }}" method="POST" enctype="multipart/form-data">
                    <input class="form-control mb-3" type="file" name="file" required>
                    <button type="submit" class="btn btn-primary">Uploader</button>
                </form>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card shadow">
            <div class="card-header bg-dark text-white">Générer des rapports</div>
            <div class="card-body text-center">
                <p>Téléchargez la liste complète des employés et statistiques au format CSV.</p>
                <a href="{{ url_for('download_report') }}" class="btn btn-success">Télécharger le Rapport</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

**`employees.html`**
```html
{% extends 'base.html' %}
{% block content %}
<h2 class="mb-4">Gestion des Employés</h2>

<div class="card shadow mb-4">
    <div class="card-body">
        <form method="POST" class="row g-3">
            <div class="col-md-3">
                <input type="text" name="name" class="form-control" placeholder="Nom" required>
            </div>
            <div class="col-md-3">
                <input type="text" name="position" class="form-control" placeholder="Poste" required>
            </div>
            <div class="col-md-4">
                <input type="email" name="email" class="form-control" placeholder="Email" required>
            </div>
            <div class="col-md-2">
                <button type="submit" class="btn btn-primary w-100">Ajouter</button>
            </div>
        </form>
    </div>
</div>

<table class="table table-striped table-hover shadow-sm bg-white">
    <thead class="table-dark">
        <tr>
            <th>ID</th>
            <th>Nom</th>
            <th>Poste</th>
            <th>Email</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for emp in employees %}
        <tr>
            <td>{{ emp.id }}</td>
            <td>{{ emp.name }}</td>
            <td>{{ emp.position }}</td>
            <td>{{ emp.email }}</td>
            <td>
                <a href="{{ url_for('delete_employee', id=emp.id) }}" class="btn btn-danger btn-sm" onclick="return confirm('Êtes-vous sûr ?')">Supprimer</a>
            </td>
        </tr>
        {% else %}
        <tr><td colspan="5" class="text-center">Aucun employé trouvé.</td></tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

### Comment lancer l'application :
1. Ouvre ton terminal dans le dossier du projet.
2. Lance le script : `python app.py`
3. Ouvre ton navigateur à l'adresse : `http://127.0.0.1:5000`
4. **Identifiants par défaut :** 
   - Utilisateur : `admin`
   - Mot de passe : `admin123` *(créés automatiquement au premier lancement)*.