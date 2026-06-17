from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coworking.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Modèles de base de données ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    reservations = db.relationship('Reservation', backref='user', lazy=True)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    reservations = db.relationship('Reservation', backref='room', lazy=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes Authentification ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash("Nom d'utilisateur déjà pris.", "danger")
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Compte créé avec succès ! Connectez-vous.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("Identifiants incorrects.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- Routes Client ---
@app.route('/')
def index():
    rooms = Room.query.all()
    return render_template('index.html', rooms=rooms)

@app.route('/book/<int:room_id>', methods=['GET', 'POST'])
@login_required
def book(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        date_str = request.form.get('date')
        start_str = request.form.get('start_time')
        end_str = request.form.get('end_time')
        
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_obj = datetime.strptime(start_str, '%H:%M').time()
        end_obj = datetime.strptime(end_str, '%H:%M').time()
        
        if start_obj >= end_obj:
            flash("L'heure de fin doit être après l'heure de début.", "danger")
            return redirect(url_for('book', room_id=room_id))
            
        # Vérification des conflits (simplifiée)
        conflict = Reservation.query.filter_by(room_id=room.id, date=date_obj).filter(
            (Reservation.start_time < end_obj) & (Reservation.end_time > start_obj)
        ).first()
        
        if conflict:
            flash("La salle est déjà réservée sur ce créneau.", "danger")
            return redirect(url_for('book', room_id=room_id))
            
        new_res = Reservation(date=date_obj, start_time=start_obj, end_time=end_obj, user_id=current_user.id, room_id=room.id)
        db.session.add(new_res)
        db.session.commit()
        flash("Réservation confirmée !", "success")
        return redirect(url_for('dashboard'))
        
    return render_template('book.html', room=room)

@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().date()
    # Trier par date
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.date.desc()).all()
    future_res = [r for r in reservations if r.date >= today]
    past_res = [r for r in reservations if r.date < today]
    return render_template('dashboard.html', future=future_res, past=past_res)

# --- Routes Admin ---
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        flash("Accès refusé.", "danger")
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        capacity = request.form.get('capacity')
        new_room = Room(name=name, capacity=capacity)
        db.session.add(new_room)
        db.session.commit()
        flash("Salle ajoutée.", "success")
        return redirect(url_for('admin'))
        
    reservations = Reservation.query.order_by(Reservation.date.desc()).all()
    return render_template('admin.html', reservations=reservations)

@app.route('/cancel/<int:res_id>')
@login_required
def cancel(res_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    res = Reservation.query.get_or_404(res_id)
    db.session.delete(res)
    db.session.commit()
    flash("Réservation annulée.", "success")
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Créer un admin par défaut si aucun n'existe
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password=generate_password_hash('admin', method='pbkdf2:sha256'), is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
    app.run(debug=True)
