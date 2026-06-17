from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coworking.db'
db = SQLAlchemy(app)

# Configuration pour Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Utilisateur(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    reservations = db.relationship('Reservation', backref='utilisateur', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Salle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False)
    reservations = db.relationship('Reservation', backref='salle', lazy=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    salle_id = db.Column(db.Integer, db.ForeignKey('salle.id'), nullable=False)
    date_reservation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_debut = db.Column(db.DateTime, nullable=False)
    date_fin = db.Column(db.DateTime, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Utilisateur.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('reservations'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user = Utilisateur(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/reservations')
@login_required
def reservations():
    reservations = Reservation.query.filter_by(utilisateur_id=current_user.id).all()
    return render_template('reservations.html', reservations=reservations)

@app.route('/reservations/toutes')
@login_required
def toutes_reservations():
    if current_user.username == 'admin':  # Fonctionnalité pour l'administrateur
        reservations = Reservation.query.all()
        return render_template('toutes_reservations.html', reservations=reservations)
    else:
        return "Accès refusé"

@app.route('/salles')
@login_required
def salles():
    salles = Salle.query.all()
    return render_template('salles.html', salles=salles)

@app.route('/reservation', methods=['GET', 'POST'])
@login_required
def faire_reservation():
    if request.method == 'POST':
        salle_id = request.form['salle_id']
        date_debut = datetime.strptime(request.form['date_debut'], '%Y-%m-%d %H:%M')
        date_fin = datetime.strptime(request.form['date_fin'], '%Y-%m-%d %H:%M')
        reservation = Reservation(utilisateur_id=current_user.id, salle_id=salle_id, date_debut=date_debut, date_fin=date_fin)
        db.session.add(reservation)
        db.session.commit()
        return redirect(url_for('reservations'))
    salles = Salle.query.all()
    return render_template('faire_reservation.html', salles=salles)

@app.route('/annuler_reservation/<int:reservation_id>')
@login_required
def annuler_reservation(reservation_id):
    if current_user.username == 'admin':  # Fonctionnalité pour l'administrateur
        reservation = Reservation.query.get(reservation_id)
        if reservation:
            db.session.delete(reservation)
            db.session.commit()
            return redirect(url_for('toutes_reservations'))
    return "Accès refusé"

@app.route('/ajouter_salle', methods=['GET', 'POST'])
@login_required
def ajouter_salle():
    if current_user.username == 'admin':  # Fonctionnalité pour l'administrateur
        if request.method == 'POST':
            nom = request.form['nom']
            salle = Salle(nom=nom)
            db.session.add(salle)
            db.session.commit()
            return redirect(url_for('salles'))
        return render_template('ajouter_salle.html')
    else:
        return "Accès refusé"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
