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
