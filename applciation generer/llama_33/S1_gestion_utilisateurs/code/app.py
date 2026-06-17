from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField, TextAreaField
from wtforms.validators import InputRequired, Email, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_clé_secrète'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///utilisateurs.db'
db = SQLAlchemy(app)

class Utilisateur(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(100), nullable=False)
    photo_profil = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    role = db.Column(db.String(10), default='utilisateur')
    actif = db.Column(db.Boolean, default=True)

    def set_mot_de_passe(self, mot_de_passe):
        self.mot_de_passe = generate_password_hash(mot_de_passe)

    def verifier_mot_de_passe(self, mot_de_passe):
        return check_password_hash(self.mot_de_passe, mot_de_passe)

class FormulaireInscription(FlaskForm):
    nom = StringField('Nom', validators=[InputRequired(), Length(min=4, max=50)])
    email = StringField('Email', validators=[InputRequired(), Email(message='Adresse email invalide'), Length(max=100)])
    mot_de_passe = PasswordField('Mot de passe', validators=[InputRequired(), Length(min=8, max=100)])
    confirmer_mot_de_passe = PasswordField('Confirmer mot de passe', validators=[InputRequired(), EqualTo('mot_de_passe')])
    submit = SubmitField('S\'inscrire')

class FormulaireConnexion(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(message='Adresse email invalide'), Length(max=100)])
    mot_de_passe = PasswordField('Mot de passe', validators=[InputRequired(), Length(min=8, max=100)])
    submit = SubmitField('Se connecter')

class FormulaireProfil(FlaskForm):
    nom = StringField('Nom', validators=[InputRequired(), Length(min=4, max=50)])
    email = StringField('Email', validators=[InputRequired(), Email(message='Adresse email invalide'), Length(max=100)])
    photo_profil = FileField('Photo de profil')
    bio = TextAreaField('Bio')
    submit = SubmitField('Mettre à jour')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'connexion'

@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))

@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    formulaire = FormulaireInscription()
    if formulaire.validate_on_submit():
        utilisateur = Utilisateur.query.filter_by(email=formulaire.email.data).first()
        if utilisateur:
            flash('Cet email est déjà utilisé.')
        else:
            nouveau_utilisateur = Utilisateur(nom=formulaire.nom.data, email=formulaire.email.data)
            nouveau_utilisateur.set_mot_de_passe(formulaire.mot_de_passe.data)
            db.session.add(nouveau_utilisateur)
            db.session.commit()
            flash('Compte créé avec succès.')
            return redirect(url_for('connexion'))
    return render_template('inscription.html', formulaire=formulaire)

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    formulaire = FormulaireConnexion()
    if formulaire.validate_on_submit():
        utilisateur = Utilisateur.query.filter_by(email=formulaire.email.data).first()
        if utilisateur and utilisateur.actif and utilisateur.verifier_mot_de_passe(formulaire.mot_de_passe.data):
            login_user(utilisateur)
            return redirect(url_for('profil'))
        else:
            flash('Email ou mot de passe incorrect, ou compte désactivé.')
    return render_template('connexion.html', formulaire=formulaire)

@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    formulaire = FormulaireProfil()
    if formulaire.validate_on_submit():
        current_user.nom = formulaire.nom.data
        current_user.email = formulaire.email.data
        if formulaire.photo_profil.data:
            photo_profil = formulaire.photo_profil.data
            photo_profil.save(os.path.join('static/images', photo_profil.filename))
            current_user.photo_profil = photo_profil.filename
        current_user.bio = formulaire.bio.data
        db.session.commit()
        flash('Profil mis à jour.')
    elif request.method == 'GET':
        formulaire.nom.data = current_user.nom
        formulaire.email.data = current_user.email
        formulaire.bio.data = current_user.bio
    return render_template('profil.html', formulaire=formulaire)

@app.route('/deconnexion')
@login_required
def deconnexion():
    logout_user()
    return redirect(url_for('connexion'))

@app.route('/admin')
@login_required
def admin():
    if current_user.role == 'admin':
        utilisateurs = Utilisateur.query.all()
        return render_template('admin.html', utilisateurs=utilisateurs)
    else:
        flash('Accès refusé.')
        return redirect(url_for('profil'))

@app.route('/desactiver/<int:user_id>')
@login_required
def desactiver(user_id):
    if current_user.role == 'admin':
        utilisateur = Utilisateur.query.get(user_id)
        if utilisateur:
            utilisateur.actif = False
            db.session.commit()
            flash('Compte désactivé.')
        else:
            flash('Utilisateur non trouvé.')
    else:
        flash('Accès refusé.')
    return redirect(url_for('admin'))

@app.route('/activer/<int:user_id>')
@login_required
def activer(user_id):
    if current_user.role == 'admin':
        utilisateur = Utilisateur.query.get(user_id)
        if utilisateur:
            utilisateur.actif = True
            db.session.commit()
            flash('Compte activé.')
        else:
            flash('Utilisateur non trouvé.')
    else:
        flash('Accès refusé.')
    return redirect(url_for('admin'))

@app.route('/changerole/<int:user_id>')
@login_required
def changerole(user_id):
    if current_user.role == 'admin':
        utilisateur = Utilisateur.query.get(user_id)
        if utilisateur:
            if utilisateur.role == 'utilisateur':
                utilisateur.role = 'admin'
            else:
                utilisateur.role = 'utilisateur'
            db.session.commit()
            flash('Rôle modifié.')
        else:
            flash('Utilisateur non trouvé.')
    else:
        flash('Accès refusé.')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
