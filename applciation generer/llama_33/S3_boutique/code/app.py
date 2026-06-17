from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from models import db, Produit, Commande, LigneCommande, Client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///boutique.db'
db.init_app(app)

login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return Client.query.get(int(user_id))

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    mot_de_passe = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')

class InscriptionForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    mot_de_passe = PasswordField('Mot de passe', validators=[DataRequired()])
    confirm_mot_de_passe = PasswordField('Confirmer mot de passe', validators=[DataRequired(), EqualTo('mot_de_passe')])
    submit = SubmitField('S\'inscrire')

class CommandeForm(FlaskForm):
    adresse = StringField('Adresse', validators=[DataRequired()])
    paiement = StringField('Paiement', validators=[DataRequired()])
    submit = SubmitField('Passer commande')

@app.route('/')
def accueil():
    produits = Produit.query.all()
    return render_template('accueil.html', produits=produits)

@app.route('/produit/<int:id>')
def fiche_produit(id):
    produit = Produit.query.get(id)
    return render_template('fiche_produit.html', produit=produit)

@app.route('/panier')
def panier():
    return render_template('panier.html')

@app.route('/commande', methods=['GET', 'POST'])
def commande():
    form = CommandeForm()
    if form.validate_on_submit():
        # Créer une nouvelle commande
        commande = Commande(client_id=current_user.id, adresse=form.adresse.data, paiement=form.paiement.data, total=0, date=datetime.now())
        db.session.add(commande)
        db.session.commit()
        return redirect(url_for('accueil'))
    return render_template('commande.html', form=form)

@app.route('/compte_client')
@login_required
def compte_client():
    commandes = Commande.query.filter_by(client_id=current_user.id).all()
    return render_template('compte_client.html', commandes=commandes)

@app.route('/admin/produits')
def admin_produits():
    produits = Produit.query.all()
    return render_template('admin/produits.html', produits=produits)

@app.route('/admin/stocks')
def admin_stocks():
    stocks = Produit.query.all()
    return render_template('admin/stocks.html', stocks=stocks)

@app.route('/admin/commandes')
def admin_commandes():
    commandes = Commande.query.all()
    return render_template('admin/commandes.html', commandes=commandes)

if __name__ == '__main__':
    app.run(debug=True)
