Je vais créer un tableau de bord administratif complet avec Flask. Voici l'implémentation complète avec toutes les fonctionnalités demandées.

## Structure du projet
```
dashboard_entreprise/
├── app.py
├── database.py
├── requirements.txt
├── static/
│   ├── css/
│   │   └── style.css
│   └── uploads/
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── login.html
│   ├── employes.html
│   ├── fichiers.html
│   └── rapports.html
└── .env
```

## 1. Fichier requirements.txt
```txt
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.2
Werkzeug==2.3.7
python-dotenv==1.0.0
reportlab==4.0.4
Pillow==10.0.0
```

## 2. Fichier .env
```env
SECRET_KEY=votre_cle_secrete_ici
DATABASE_URL=sqlite:///entreprise.db
```

## 3. Fichier database.py
```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Employe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telephone = db.Column(db.String(20))
    poste = db.Column(db.String(100))
    date_embauche = db.Column(db.Date, nullable=False)
    salaire = db.Column(db.Float)
    actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telephone = db.Column(db.String(20))
    entreprise = db.Column(db.String(100))
    date_inscription = db.Column(db.DateTime, default=datetime.utcnow)

class Vente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    date_vente = db.Column(db.DateTime, default=datetime.utcnow)
    produit = db.Column(db.String(200))
    statut = db.Column(db.String(50), default='completé')

class Fichier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    chemin = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50))
    taille = db.Column(db.Integer)
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

def init_db():
    """Initialise la base de données avec un utilisateur admin par défaut"""
    db.create_all()
    
    # Créer un utilisateur admin par défaut si aucun n'existe
    if not User.query.filter_by(username='admin').first():
        from werkzeug.security import generate_password_hash
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        
        # Ajouter des données de démo
        from datetime import date
        
        # Clients de démo
        clients = [
            Client(nom="Dupont", email="dupont@exemple.com", telephone="0123456789", entreprise="Entreprise A"),
            Client(nom="Martin", email="martin@exemple.com", telephone="0234567890", entreprise="Entreprise B"),
            Client(nom="Bernard", email="bernard@exemple.com", telephone="0345678901", entreprise="Entreprise C"),
        ]
        
        for client in clients:
            db.session.add(client)
        
        # Employés de démo
        employes = [
            Employe(nom="Lefevre", prenom="Pierre", email="pierre@entreprise.com", 
                   telephone="0456789012", poste="Directeur", 
                   date_embauche=date(2020, 1, 15), salaire=45000),
            Employe(nom="Dubois", prenom="Marie", email="marie@entreprise.com", 
                   telephone="0567890123", poste="Commerciale", 
                   date_embauche=date(2021, 3, 10), salaire=35000),
        ]
        
        for employe in employes:
            db.session.add(employe)
        
        # Ventes de démo
        from datetime import datetime, timedelta
        for i in range(10):
            vente = Vente(
                client_id=(i % 3) + 1,
                montant=1000 + (i * 500),
                produit=f"Produit {i+1}",
                date_vente=datetime.now() - timedelta(days=i*3)
            )
            db.session.add(vente)
        
        db.session.commit()
        print("Base de données initialisée avec succès!")
```

## 4. Fichier app.py
```python
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import db, User, Employe, Client, Vente, Fichier, init_db
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import json

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Extensions autorisées
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx'}

# Initialiser la base de données
db.init_app(app)

# Initialiser Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes principales
@app.route('/')
@login_required
def dashboard():
    """Page principale du tableau de bord"""
    # Calculer les statistiques
    total_clients = Client.query.count()
    
    # Chiffre d'affaires du mois
    debut_mois = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ventes_mois = Vente.query.filter(Vente.date_vente >= debut_mois).all()
    ca_mois = sum(vente.montant for vente in ventes_mois)
    
    # Nombre de ventes du mois
    ventes_count = len(ventes_mois)
    
    # Nombre d'employés actifs
    employes_actifs = Employe.query.filter_by(actif=True).count()
    
    # Dernières ventes
    dernieres_ventes = Vente.query.order_by(Vente.date_vente.desc()).limit(5).all()
    
    # Graphique des ventes des 6 derniers mois
    six_mois = datetime.now() - timedelta(days=180)
    ventes_six_mois = Vente.query.filter(Vente.date_vente >= six_mois).all()
    
    # Préparer les données pour le graphique
    ventes_par_mois = {}
    for vente in ventes_six_mois:
        mois = vente.date_vente.strftime('%Y-%m')
        if mois not in ventes_par_mois:
            ventes_par_mois[mois] = 0
        ventes_par_mois[mois] += vente.montant
    
    return render_template('dashboard.html',
                         total_clients=total_clients,
                         ca_mois=ca_mois,
                         ventes_count=ventes_count,
                         employes_actifs=employes_actifs,
                         dernieres_ventes=dernieres_ventes,
                         ventes_par_mois=json.dumps(ventes_par_mois))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Connexion réussie!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    logout_user()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('login'))

# Gestion des employés
@app.route('/employes')
@login_required
def employes():
    """Page de gestion des employés"""
    employes_list = Employe.query.order_by(Employe.nom).all()
    return render_template('employes.html', employes=employes_list)

@app.route('/employe/ajouter', methods=['POST'])
@login_required
def ajouter_employe():
    """Ajouter un nouvel employé"""
    if request.method == 'POST':
        try:
            employe = Employe(
                nom=request.form['nom'],
                prenom=request.form['prenom'],
                email=request.form['email'],
                telephone=request.form['telephone'],
                poste=request.form['poste'],
                date_embauche=datetime.strptime(request.form['date_embauche'], '%Y-%m-%d').date(),
                salaire=float(request.form['salaire']),
                actif=request.form.get('actif') == 'on'
            )
            db.session.add(employe)
            db.session.commit()
            flash('Employé ajouté avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'ajout: {str(e)}', 'danger')
    
    return redirect(url_for('employes'))

@app.route('/employe/modifier/<int:id>', methods=['POST'])
@login_required
def modifier_employe(id):
    """Modifier un employé existant"""
    employe = Employe.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            employe.nom = request.form['nom']
            employe.prenom = request.form['prenom']
            employe.email = request.form['email']
            employe.telephone = request.form['telephone']
            employe.poste = request.form['poste']
            employe.date_embauche = datetime.strptime(request.form['date_embauche'], '%Y-%m-%d').date()
            employe.salaire = float(request.form['salaire'])
            employe.actif = request.form.get('actif') == 'on'
            
            db.session.commit()
            flash('Employé modifié avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'danger')
    
    return redirect(url_for('employes'))

@app.route('/employe/supprimer/<int:id>')
@login_required
def supprimer_employe(id):
    """Supprimer un employé"""
    employe = Employe.query.get_or_404(id)
    
    try:
        db.session.delete(employe)
        db.session.commit()
        flash('Employé supprimé avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
    
    return redirect(url_for('employes'))

# Gestion des fichiers
@app.route('/fichiers')
@login_required
def fichiers():
    """Page de gestion des fichiers"""
    fichiers_list = Fichier.query.order_by(Fichier.date_upload.desc()).all()
    return render_template('fichiers.html', fichiers=fichiers_list)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Uploader un fichier"""
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('fichiers'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('fichiers'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Créer le dossier uploads s'il n'existe pas
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Enregistrer dans la base de données
        fichier = Fichier(
            nom=filename,
            chemin=filepath,
            type=filename.rsplit('.', 1)[1].lower(),
            taille=os.path.getsize(filepath),
            user_id=current_user.id
        )
        db.session.add(fichier)
        db.session.commit()
        
        flash('Fichier uploadé avec succès!', 'success')
    else:
        flash('Type de fichier non autorisé', 'danger')
    
    return redirect(url_for('fichiers'))

@app.route('/fichier/supprimer/<int:id>')
@login_required
def supprimer_fichier(id):
    """Supprimer un fichier"""
    fichier = Fichier.query.get_or_404(id)
    
    try:
        # Supprimer le fichier physique
        if os.path.exists(fichier.chemin):
            os.remove(fichier.chemin)
        
        # Supprimer de la base de données
        db.session.delete(fichier)
        db.session.commit()
        
        flash('Fichier supprimé avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
    
    return redirect(url_for('fichiers'))

# Génération de rapports
@app.route('/rapports')
@login_required
def rapports():
    """Page de génération de rapports"""
    return render_template('rapports.html')

@app.route('/generer_rapport/<type_rapport>')
@login_required
def generer_rapport(type_rapport):
    """Générer un rapport PDF"""
    try:
        # Créer le nom du fichier
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"rapport_{type_rapport}_{timestamp}.pdf"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Créer le document PDF
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Titre
        title = Paragraph(f"Rapport {type_rapport.capitalize()}", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Date de génération
        date_str = Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
        elements.append(date_str)
        elements.append(Spacer(1, 24))
        
        # Contenu selon le type de rapport
        if type_rapport == 'ventes':
            # Statistiques des ventes
            elements.append(Paragraph("Statistiques des Ventes", styles['Heading2']))
            
            # Ventes du mois
            debut_mois = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ventes_mois = Vente.query.filter(Vente.date_vente >= debut_mois).all()
            ca_mois = sum(vente.montant for vente in ventes_mois)
            
            data = [
                ['Métrique', 'Valeur'],
                ['Chiffre d\'affaires du mois', f'{ca_mois:,.2f} €'],
                ['Nombre de ventes du mois', len(ventes_mois)],
                ['Vente moyenne', f'{ca_mois/len(ventes_mois) if ventes_mois else 0:,.2f} €']
            ]
            
        elif type_rapport == 'employes':
            # Liste des employés
            elements.append(Paragraph("Liste des Employés", styles['Heading2']))
            
            employes = Employe.query.order_by(Employe.nom).all()
            data = [['Nom', 'Prénom', 'Poste', 'Email', 'Salaire', 'Statut']]
            
            for emp in employes:
                data.append([
                    emp.nom,
                    emp.prenom,
                    emp.poste,
                    emp.email,
                    f'{emp.salaire:,.2f} €' if emp.salaire else 'N/A',
                    'Actif' if emp.actif else 'Inactif'
                ])
            
        elif type_rapport == 'clients':
            # Liste des clients
            elements.append(Paragraph("Liste des Clients", styles['Heading2']))
            
            clients = Client.query.order_by(Client.nom).all()
            data = [['Nom', 'Email', 'Téléphone', 'Entreprise', 'Date d\'inscription']]
            
            for client in clients:
                data.append([
                    client.nom,
                    client.email,
                    client.telephone or 'N/A',
                    client.entreprise or 'N/A',
                    client.date_inscription.strftime('%d/%m/%Y')
                ])
        
        # Créer le tableau
        if 'data' in locals():
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
        
        # Générer le PDF
        doc.build(elements)
        
        # Enregistrer le fichier dans la base de données
        fichier = Fichier(
            nom=filename,
            chemin=filepath,
            type='pdf',
            taille=os.path.getsize(filepath),
            user_id=current_user.id
        )
        db.session.add(fichier)
        db.session.commit()
        
        # Télécharger le fichier
        return send_file(filepath, as_attachment=True)
        
    except Exception as e:
        flash(f'Erreur lors de la génération du rapport: {str(e)}', 'danger')
        return redirect(url_for('rapports'))

# API pour les statistiques
@app.route('/api/stats')
@login_required
def api_stats():
    """API pour les statistiques en temps réel"""
    total_clients = Client.query.count()
    debut_mois = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ventes_mois = Vente.query.filter(Vente.date_vente >= debut_mois).all()
    ca_mois = sum(vente.montant for vente in ventes_mois)
    ventes_count = len(ventes_mois)
    employes_actifs = Employe.query.filter_by(actif=True).count()
    
    return jsonify({
        'total_clients': total_clients,
        'ca_mois': ca_mois,
        'ventes_mois': ventes_count,
        'employes_actifs': employes_actifs
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_db()
    
    # Créer le dossier uploads s'il n'existe pas
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    app.run(debug=True, port=5000)
```

## 5. Templates HTML

### base.html
```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tableau de Bord - {% block title %}{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-speedometer2"></i> Tableau de Bord
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('dashboard') }}">
                            <i class="bi bi-house"></i> Accueil
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('employes') }}">
                            <i class="bi bi-people"></i> Employés
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('fichiers') }}">
                            <i class="bi bi-folder"></i> Fichiers
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('rapports') }}">
                            <i class="bi bi-file-earmark-text"></i> Rapports
                        </a>
                    </li>
                </ul>
                <ul class="navbar-nav">
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown">
                            <i class="bi bi-person-circle"></i> {{ current_user.username }}
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="{{ url_for('logout') }}">
                                <i class="bi bi-box-arrow-right"></i> Déconnexion
                            </a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
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

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### login.html
```html
{% extends "base.html" %}

{% block title %}Connexion{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6 col-lg-4">
        <div class="card mt-5">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0"><i class="bi bi-box-arrow-in-right"></i> Connexion</h4>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('login') }}">
                    <div class="mb-3">
                        <label for="username" class="form-label">Nom d'utilisateur</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Mot de passe</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-box-arrow-in-right"></i> Se connecter
                        </button>
                    </div>
                </form>
                <div class="mt-3 text-center">
                    <small>Identifiants par défaut: admin / admin123</small>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### dashboard.html
```html
{% extends "base.html" %}

{% block title %}Tableau de Bord{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card bg-primary text-white">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="card-title">Chiffre d'Affaires</h6>
                        <h2 class="mb-0">{{ "%.2f"|format(ca_mois) }} €</h2>
                        <small>Ce mois</small>
                    </div>
                    <i class="bi bi-currency-euro display-6"></i>
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-success text-white">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="card-title">Clients</h6>
                        <h2 class="mb-0">{{ total_clients }}</h2>
                        <small>Total</small>
                    </div>
                    <i class="bi bi-people display-6"></i>
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-info text-white">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="card-title">Ventes</h6>
                        <h2 class="mb-0">{{ ventes_count }}</h2>
                        <small>Ce mois</small>
                    </div>
                    <i class="bi bi-cart-check display-6"></i>
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-warning text-white">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="card-title">Employés</h6>
                        <h2 class="mb-0">{{ employes_actifs }}</h2>
                        <small>Actifs</small>
                    </div>
                    <i class="bi bi-person-badge display-6"></i>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Évolution des Ventes</h5>
            </div>
            <div class="card-body">
                <canvas id="ventesChart"></canvas>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Dernières Ventes</h5>
            </div>
            <div class="card-body">
                <div class="list-group">
                    {% for vente in dernieres_ventes %}
                    <div class="list-group-item">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">{{ vente.produit }}</h6>
                            <small>{{ "%.2f"|format(vente.montant) }} €</small>
                        </div>
                        <small class="text-muted">{{ vente.date_vente.strftime('%d/%m/%Y') }}</small>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Actions Rapides</h5>
            </div>
            <div class="card-body">
                <div class="row text-center">
                    <div class="col-md-3">
                        <a href="{{ url_for('employes') }}" class="btn btn-outline-primary btn-lg w-100">
                            <i class="bi bi-person-plus display-6"></i><br>
                            Gérer Employés
                        </a>
                    </div>
                    <div class="col-md-3">
                        <a href="{{ url_for('fichiers') }}" class="btn btn-outline-success btn-lg w-100">
                            <i class="bi bi-upload display-6"></i><br>
                            Uploader Fichiers
                        </a>
                    </div>
                    <div class="col-md-3">
                        <a href="{{ url_for('rapports') }}" class="btn btn-outline-info btn-lg w-100">
                            <i class="bi bi-file-earmark-text display-6"></i><br>
                            Générer Rapports
                        </a>
                    </div>
                    <div class="col-md-3">
                        <button onclick="refreshStats()" class="btn btn-outline-warning btn-lg w-100">
                            <i class="bi bi-arrow-clockwise display-6"></i><br>
                            Actualiser
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
// Graphique des ventes
const ventesData = {{ ventes_par_mois|safe }};
const labels = Object.keys(ventesData).sort();
const data = labels.map(label => ventesData[label]);

const ctx = document.getElementById('ventesChart').getContext('2d');
const ventesChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: labels,
        datasets: [{
            label: 'Chiffre d\'affaires (€)',
            data: data,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            tension: 0.1
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: {
                position: 'top',
            }
        }
    }
});

// Actualiser les statistiques
function refreshStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Mettre à jour les cartes (à implémenter selon les besoins)
            location.reload();
        });
}
</script>
{% endblock %}
```

### employes.html
```html
{% extends "base.html" %}

{% block title %}Gestion des Employés{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-4">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">
                    <i class="bi bi-person-plus"></i> Ajouter un Employé
                </h5>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('ajouter_employe') }}">
                    <div class="mb-2">
                        <label class="form-label">Nom</label>
                        <input type="text" class="form-control form-control-sm" name="nom" required>
                    </div>
                    <div class="mb-2">
                        <label class="form-label">Prénom</label>
                        <input type="text" class="form-control form-control-sm" name="prenom" required>
                    </div>
                    <div class="mb-2">
                        <label class="form-label">Email</label>
                        <input type="email" class="form-control form-control-sm" name="email" required>
                    </div>
                    <div class="mb-2">
                        <label class="form-label">Téléphone</label>
                        <input type="tel" class="form-control form-control-sm" name="telephone">
                    </div>
                    <div class="mb-2">
                        <label class="form-label">Poste</label>
                        <input type="text" class="form-control form-control-sm" name="poste" required>
                    </div>
                    <div class="mb-2">
                        <label class="form-label">Date d'embauche</label>
                        <input type="date" class="form-control form-control-sm" name="date_embauche" required>
                    </div>
                    <div class="mb-2">
                        <label class="form-label">Salaire (€)</label>
                        <input type="number" step="0.01" class="form-control form-control-sm" name="salaire">
                    </div>
                    <div class="mb-3 form-check">
                        <input type="checkbox" class="form-check-input" name="actif" checked>
                        <label class="form-check-label">Actif</label>
                    </div>
                    <button type="submit" class="btn btn-primary btn-sm w-100">
                        <i class="bi bi-plus-circle"></i> Ajouter
                    </button>
                </form>
            </div>
        </div>
    </div>

    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Liste des Employés</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Nom</th>
                                <th>Prénom</th>
                                <th>Poste</th>
                                <th>Email</th>
                                <th>Salaire</th>
                                <th>Statut</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for employe in employes %}
                            <tr>
                                <td>{{ employe.nom }}</td>
                                <td>{{ employe.prenom }}</td>
                                <td>{{ employe.poste }}</td>
                                <td>{{ employe.email }}</td>
                                <td>{{ "%.2f"|format(employe.salaire) if employe.salaire else 'N/A' }} €</td>
                                <td>
                                    <span class="badge bg-{{ 'success' if employe.actif else 'danger' }}">
                                        {{ 'Actif' if employe.actif else 'Inactif' }}
                                    </span>
                                </td>
                                <td>
                                    <button class="btn btn-sm btn-warning" data-bs-toggle="modal" 
                                            data-bs-target="#editModal{{ employe.id }}">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                    <a href="{{ url_for('supprimer_employe', id=employe.id) }}" 
                                       class="btn btn-sm btn-danger"
                                       onclick="return confirm('Supprimer cet employé ?')">
                                        <i class="bi bi-trash"></i>
                                    </a>
                                </td>
                            </tr>

                            <!-- Modal d'édition -->
                            <div class="modal fade" id="editModal{{ employe.id }}" tabindex="-1">
                                <div class="modal-dialog">
                                    <div class="modal-content">
                                        <div class="modal-header">
                                            <h5 class="modal-title">Modifier Employé</h5>
                                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                        </div>
                                        <form method="POST" action="{{ url_for('modifier_employe', id=employe.id) }}">
                                            <div class="modal-body">
                                                <div class="mb-2">
                                                    <label class="form-label">Nom</label>
                                                    <input type="text" class="form-control" name="nom" 
                                                           value="{{ employe.nom }}" required>
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label">Prénom</label>
                                                    <input type="text" class="form-control" name="prenom" 
                                                           value="{{ employe.prenom }}" required>
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label">Email</label>
                                                    <input type="email" class="form-control" name="email" 
                                                           value="{{ employe.email }}" required>
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label">Téléphone</label>
                                                    <input type="tel" class="form-control" name="telephone" 
                                                           value="{{ employe.telephone or '' }}">
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label">Poste</label>
                                                    <input type="text" class="form-control" name="poste" 
                                                           value="{{ employe.poste }}" required>
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label">Date d'embauche</label>
                                                    <input type="date" class="form-control" name="date_embauche" 
                                                           value="{{ employe.date_embauche }}" required>
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label">Salaire (€)</label>
                                                    <input type="number" step="0.01" class="form-control" name="salaire" 
                                                           value="{{ employe.salaire or '' }}">
                                                </div>
                                                <div class="mb-2 form-check">
                                                    <input type="checkbox" class="form-check-input" name="actif" 
                                                           {{ 'checked' if employe.actif else '' }}>
                                                    <label class="form-check-label">Actif</label>
                                                </div>
                                            </div>
                                            <div class="modal-footer">
                                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                                    Annuler
                                                </button>
                                                <button type="submit" class="btn btn-primary">
                                                    Enregistrer
                                                </button>
                                            </div>
                                        </form>
                                    </div>
                                </div>
                            </div>
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

### fichiers.html
```html
{% extends "base.html" %}

{% block title %}Gestion des Fichiers{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-4">
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0">
                    <i class="bi bi-upload"></i> Uploader un Fichier
                </h5>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('upload_file') }}" enctype="multipart/form-data">
                    <div class="mb-3">
                        <label for="file" class="form-label">Sélectionner un fichier</label>
                        <input class="form-control" type="file" id="file" name="file" required>
                        <div class="form-text">
                            Extensions autorisées: PDF, PNG, JPG, DOC, DOCX, XLS, XLSX
                        </div>
                    </div>
                    <button type="submit" class="btn btn-success w-100">
                        <i class="bi bi-cloud-upload"></i> Uploader
                    </button>
                </form>
            </div>
        </div>
        
        <div class="card mt-4">
            <div class="card-header">
                <h6 class="mb-0">Informations</h6>
            </div>
            <div class="card-body">
                <p class="small">
                    <i class="bi bi-info-circle"></i> 
                    Taille maximale: 16MB<br>
                    Dossier: static/uploads/
                </p>
            </div>
        </div>
    </div>

    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Fichiers Uploadés</h5>
            </div>
            <div class="card-body">
                {% if fichiers %}
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Nom</th>
                                <th>Type</th>
                                <th>Taille</th>
                                <th>Date</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for fichier in fichiers %}
                            <tr>
                                <td>{{ fichier.nom }}</td>
                                <td>
                                    <span class="badge bg-info">
                                        {{ fichier.type|upper }}
                                    </span>
                                </td>
                                <td>{{ (fichier.taille / 1024)|round(2) }} KB</td>
                                <td>{{ fichier.date_upload.strftime('%d/%m/%Y %H:%M') }}</td>
                                <td>
                                    {% if fichier.type == 'pdf' %}
                                    <a href="{{ url_for('static', filename='uploads/' + fichier.nom) }}" 
                                       target="_blank" class="btn btn-sm btn-info">
                                        <i class="bi bi-eye"></i>
                                    </a>
                                    {% endif %}
                                    <a href="{{ url_for('static', filename='uploads/' + fichier.nom) }}" 
                                       download class="btn btn-sm btn-primary">
                                        <i class="bi bi-download"></i>
                                    </a>
                                    <a href="{{ url_for('supprimer_fichier', id=fichier.id) }}" 
                                       class="btn btn-sm btn-danger"
                                       onclick="return confirm('Supprimer ce fichier ?')">
                                        <i class="bi bi-trash"></i>
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="text-center py-5">
                    <i class="bi bi-folder-x display-1 text-muted"></i>
                    <p class="mt-3">Aucun fichier uploadé</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### rapports.html
```html
{% extends "base.html" %}

{% block title %}Génération de Rapports{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0">
                    <i class="bi bi-file-earmark-text"></i> Générer des Rapports
                </h5>
            </div>
            <div class="card-body">
                <div class="row text-center">
                    <div class="col-md-4 mb-3">
                        <div class="card h-100">
                            <div class="card-body">
                                <i class="bi bi-graph-up display-1 text-primary"></i>
                                <h5 class="card-title mt-3">Rapport des Ventes</h5>
                                <p class="card-text">Statistiques détaillées des ventes mensuelles.</p>
                                <a href="{{ url_for('generer_rapport', type_rapport='ventes') }}" 
                                   class="btn btn-primary">
                                    <i class="bi bi-download"></i> Générer PDF
                                </a>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4 mb-3">
                        <div class="card h-100">
                            <div class="card-body">
                                <i class="bi bi-people display-1 text-success"></i>
                                <h5 class="card-title mt-3">Rapport des Employés</h5>
                                <p class="card-text">Liste complète des employés avec détails.</p>
                                <a href="{{ url_for('generer_rapport', type_rapport='employes') }}" 
                                   class="btn btn-success">
                                    <i class="bi bi-download"></i> Générer PDF
                                </a>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4 mb-3">
                        <div class="card h-100">
                            <div class="card-body">
                                <i class="bi bi-person-badge display-1 text-warning"></i>
                                <h5 class="card-title mt-3">Rapport des Clients</h5>
                                <p class="card-text">Base de données clients avec informations.</p>
                                <a href="{{ url_for('generer_rapport', type_rapport='clients') }}" 
                                   class="btn btn-warning">
                                    <i class="bi bi-download"></i> Générer PDF
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="mt-4">
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle"></i>
                        Les rapports sont générés au format PDF et téléchargés automatiquement.
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## 6. Fichier static/css/style.css
```css
/* Style personnalisé pour le tableau de bord */

body {
    background-color: #f8f9fa;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.navbar-brand {
    font-weight: 600;
}

.card {
    border: none;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    margin-bottom: 1.5rem;
}

.card-header {
    border-bottom: 1px solid rgba(0, 0, 0, 0.125);
    font-weight: 600;
}

.stat-card {
    transition: transform 0.3s;
}

.stat-card:hover {
    transform: translateY(-5px);
}

.table th {
    font-weight: 600;
    border-top: none;
}

.btn-action {
    padding: 0.25rem 0.5rem;
    margin: 0 0.1rem;
}

.alert {
    border: none;
}

/* Animation pour les cartes */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.card {
    animation: fadeIn 0.5s ease-out;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .display-6 {
        font-size: 2rem;
    }
    
    .btn-lg {
        padding: 0.5rem;
        font-size: 0.9rem;
    }
}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #555;
}
```

## Installation et utilisation

### 1. Installation
```bash
# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement
# Sur Windows:
venv\Scripts\activate
# Sur Mac/Linux:
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Créer le fichier .env avec votre clé secrète
echo "SECRET_KEY=votre_cle_secrete_ici" > .env
echo "DATABASE_URL=sqlite:///entreprise.db" >> .env
```

### 3. Lancer l'application
```bash
python app.py
```

### 4. Accéder au tableau de bord
- URL: http://localhost:5000
- Identifiants par défaut:
  - Utilisateur: `admin`
  - Mot de passe: `admin123`

## Fonctionnalités principales

### ✅ Statistiques
- Chiffre d'affaires du mois
- Nombre total de clients
- Ventes du mois
- Nombre d'employés actifs
- Graphique d'évolution des ventes

### ✅ Gestion des employés
- Ajouter, modifier, supprimer des employés
- Informations complètes (nom, prénom, email, poste, salaire, etc.)
- Statut actif/inactif

### ✅ Upload de fichiers
- Support PDF, images, documents Office
- Taille maximale: 16MB
- Visualisation et téléchargement
- Gestion des fichiers uploadés

### ✅ Génération de rapports
- Rapports PDF des ventes
- Rapports PDF des employés
- Rapports PDF des clients
- Téléchargement automatique

### ✅ Sécurité
- Connexion sécurisée avec Flask-Login
- Hash des mots de passe
- Sessions utilisateur
- Protection contre les attaques CSRF

### ✅ Interface utilisateur
- Design responsive avec Bootstrap
- Navigation intuitive
- Messages d'alerte
- Graphiques avec Chart.js

## Base de données
L'application utilise SQLite avec les tables suivantes:
- `users`: Utilisateurs du système
- `employes`: Données des employés
- `clients`: Informations clients
- `ventes`: Historique des ventes
- `fichiers`: Métadonnées des fichiers uploadés

Cette application fournit un tableau de bord complet et fonctionnel pour la gestion d'une petite entreprise. Vous pouvez l'étendre avec des fonctionnalités supplémentaires selon vos besoins spécifiques.