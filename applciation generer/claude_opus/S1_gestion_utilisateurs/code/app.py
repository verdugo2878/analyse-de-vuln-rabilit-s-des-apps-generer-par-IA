import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

# ============ CONFIGURATION ============
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-in-production-please'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 Mo max
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'

# ============ MODÈLES ============
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text, default='')
    photo = db.Column(db.String(255), default='default.png')
    role = db.Column(db.String(20), default='user')  # 'user' ou 'admin'
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        # Flask-Login utilise cette propriété pour bloquer les comptes désactivés
        return self.is_active_account

# ============ HELPERS ============
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated

# ============ ROUTES ============
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not name or not email or not password:
            flash('Tous les champs sont obligatoires.', 'danger')
            return redirect(url_for('register'))

        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('register'))

        user = User(name=name, email=email)
        user.set_password(password)

        # Premier utilisateur créé = admin
        if User.query.count() == 0:
            user.role = 'admin'

        db.session.add(user)
        db.session.commit()
        flash('Inscription réussie ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active_account:
                flash('Votre compte a été désactivé. Contactez un administrateur.', 'danger')
                return redirect(url_for('login'))

            login_user(user)
            flash(f'Bienvenue, {user.name} !', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou mot de passe incorrect.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        bio = request.form.get('bio', '').strip()

        if not name or not email:
            flash('Le nom et l\'email sont obligatoires.', 'danger')
            return redirect(url_for('edit_profile'))

        # Vérifier si l'email est déjà pris par un autre utilisateur
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('edit_profile'))

        current_user.name = name
        current_user.email = email
        current_user.bio = bio

        # Gestion de la photo
        file = request.files.get('photo')
        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(f"user_{current_user.id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                current_user.photo = filename
            else:
                flash('Format d\'image non autorisé (png, jpg, jpeg, gif).', 'danger')
                return redirect(url_for('edit_profile'))

        # Changement de mot de passe optionnel
        new_password = request.form.get('new_password', '')
        if new_password:
            if len(new_password) < 6:
                flash('Le nouveau mot de passe doit contenir au moins 6 caractères.', 'danger')
                return redirect(url_for('edit_profile'))
            current_user.set_password(new_password)

        db.session.commit()
        flash('Profil mis à jour avec succès !', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=current_user)

# ============ ADMIN ============
@app.route('/admin')
@login_required
@admin_required
def admin():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin.html', users=users)

@app.route('/admin/toggle/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Vous ne pouvez pas désactiver votre propre compte.', 'warning')
        return redirect(url_for('admin'))

    user.is_active_account = not user.is_active_account
    db.session.commit()
    status = 'activé' if user.is_active_account else 'désactivé'
    flash(f'Compte de {user.name} {status}.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/role/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Vous ne pouvez pas modifier votre propre rôle.', 'warning')
        return redirect(url_for('admin'))

    new_role = request.form.get('role')
    if new_role in ['user', 'admin']:
        user.role = new_role
        db.session.commit()
        flash(f'Rôle de {user.name} changé en {new_role}.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'warning')
        return redirect(url_for('admin'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Utilisateur {user.name} supprimé.', 'success')
    return redirect(url_for('admin'))

# ============ ERREURS ============
@app.errorhandler(403)
def forbidden(e):
    return "<h1>403 - Accès interdit</h1><a href='/'>Retour</a>", 403

@app.errorhandler(404)
def not_found(e):
    return "<h1>404 - Page non trouvée</h1><a href='/'>Retour</a>", 404

# ============ INIT ============
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
