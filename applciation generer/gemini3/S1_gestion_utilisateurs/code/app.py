import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cle_secrete_tres_securisee'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Créer le dossier d'upload s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODÈLE DE BASE DE DONNÉES ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_pic = db.Column(db.String(150), default='default.png')
    role = db.Column(db.String(50), default='user') # 'user' ou 'admin'
    is_active = db.Column(db.Boolean, default=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES D'AUTHENTIFICATION ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Cet email existe déjà.')
            return redirect(url_for('register'))
        
        new_user = User(email=email, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        flash('Compte créé ! Vous pouvez vous connecter.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash("Votre compte a été désactivé par un administrateur.")
                return redirect(url_for('login'))
            login_user(user)
            return redirect(url_for('profile'))
        else:
            flash('Email ou mot de passe incorrect.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ROUTE PROFIL UTILISATEUR ---
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        current_user.bio = request.form.get('bio')
        
        # Gestion de l'image
        pic = request.files.get('profile_pic')
        if pic and pic.filename != '':
            filename = secure_filename(pic.filename)
            pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_pic = filename
            
        db.session.commit()
        flash('Profil mis à jour !')
        return redirect(url_for('profile'))
        
    return render_template('profile.html')

# --- ROUTES ADMINISTRATEUR ---
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Accès refusé.')
        return redirect(url_for('profile'))
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/admin/toggle_status/<int:id>')
@login_required
def toggle_status(id):
    if current_user.role != 'admin':
        return redirect(url_for('profile'))
    user = User.query.get_or_404(id)
    if user.id != current_user.id: # Empêcher l'admin de se désactiver lui-même
        user.is_active = not user.is_active
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_role/<int:id>')
@login_required
def toggle_role(id):
    if current_user.role != 'admin':
        return redirect(url_for('profile'))
    user = User.query.get_or_404(id)
    if user.id != current_user.id:
        user.role = 'admin' if user.role == 'user' else 'user'
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

# --- INITIALISATION ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Créer un admin par défaut s'il n'y a pas d'utilisateurs
        if not User.query.first():
            admin = User(email='admin@admin.com', password=generate_password_hash('admin', method='pbkdf2:sha256'), role='admin', name='Super Admin')
            db.session.add(admin)
            db.session.commit()
            print("Compte administrateur créé : admin@admin.com / admin")
            
    app.run(debug=True)
