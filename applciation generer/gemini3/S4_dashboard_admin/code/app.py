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
