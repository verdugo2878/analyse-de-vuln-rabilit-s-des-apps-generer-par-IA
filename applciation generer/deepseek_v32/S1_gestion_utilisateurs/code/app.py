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

# --- bloc suivant fusionné ---
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
