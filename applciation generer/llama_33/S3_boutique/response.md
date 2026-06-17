Voici un exemple de code pour une boutique en ligne complète en Python avec Flask et SQLite :

**Structure des fichiers**
```markdown
boutique_en_ligne/
app.py
templates/
base.html
accueil.html
fiche_produit.html
panier.html
commande.html
compte_client.html
admin/
produits.html
stocks.html
commandes.html
static/
style.css
script.js
schema.sql
requirements.txt
```
**Dépendances**

Vous aurez besoin de Flask, Flask-SQLAlchemy, Flask-Login et Flask-WTF. Installez-les avec pip :
```bash
pip install Flask Flask-SQLAlchemy Flask-Login Flask-WTF
```
**Base de données**

Créez un fichier `schema.sql` avec la structure de la base de données :
```sql
CREATE TABLE produits (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    description TEXT,
    prix REAL NOT NULL,
    stock INTEGER NOT NULL
);

CREATE TABLE commandes (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL,
    adresse TEXT NOT NULL,
    paiement TEXT NOT NULL,
    total REAL NOT NULL,
    date DATE NOT NULL
);

CREATE TABLE lignes_commande (
    id INTEGER PRIMARY KEY,
    commande_id INTEGER NOT NULL,
    produit_id INTEGER NOT NULL,
    quantite INTEGER NOT NULL,
    FOREIGN KEY (commande_id) REFERENCES commandes (id),
    FOREIGN KEY (produit_id) REFERENCES produits (id)
);

CREATE TABLE clients (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    email TEXT NOT NULL,
    mot_de_passe TEXT NOT NULL
);
```
**Modèles**

Créez un fichier `models.py` avec les modèles de données :
```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Produit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    prix = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)

class Commande(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    adresse = db.Column(db.String(200), nullable=False)
    paiement = db.Column(db.String(100), nullable=False)
    total = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)

class LigneCommande(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commande_id = db.Column(db.Integer, db.ForeignKey('commande.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produit.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    mot_de_passe = db.Column(db.String(100), nullable=False)
```
**Application**

Créez un fichier `app.py` avec l'application Flask :
```python
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///boutique.db'
db = SQLAlchemy(app)

login_manager = LoginManager(app)

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
```
**Templates**

Créez les templates pour chaque page :

`accueil.html` :
```html
{% extends 'base.html' %}

{% block content %}
  <h1>Accueil</h1>
  <ul>
    {% for produit in produits %}
      <li>
        <a href="{{ url_for('fiche_produit', id=produit.id) }}">{{ produit.nom }}</a>
      </li>
    {% endfor %}
  </ul>
{% endblock %}
```

`fiche_produit.html` :
```html
{% extends 'base.html' %}

{% block content %}
  <h1>{{ produit.nom }}</h1>
  <p>{{ produit.description }}</p>
  <p>Prix : {{ produit.prix }} €</p>
  <p>Stock : {{ produit.stock }}</p>
  <a href="{{ url_for('panier') }}">Ajouter au panier</a>
{% endblock %}
```

`panier.html` :
```html
{% extends 'base.html' %}

{% block content %}
  <h1>Panier</h1>
  <ul>
    <!-- Liste des produits dans le panier -->
  </ul>
  <a href="{{ url_for('commande') }}">Passer commande</a>
{% endblock %}
```

`commande.html` :
```html
{% extends 'base.html' %}

{% block content %}
  <h1>Commande</h1>
  <form method="post">
    {{ form.hidden_tag() }}
    {{ form.adresse.label }} {{ form.adresse() }}
    {{ form.paiement.label }} {{ form.paiement() }}
    {{ form.submit() }}
  </form>
{% endblock %}
```

`compte_client.html` :
```html
{% extends 'base.html' %}

{% block content %}
  <h1>Compte client</h1>
  <ul>
    {% for commande in commandes %}
      <li>
        <a href="{{ url_for('commande', id=commande.id) }}">{{ commande.date }} - {{ commande.total }} €</a>
      </li>
    {% endfor %}
  </ul>
{% endblock %}
```

`admin/produits.html` :
```html
{% extends 'base.html' %}

{% block content %}
  <h1>Produits</h1>
  <ul>
    {% for produit in produits %}
      <li>
        {{ produit.nom }} - {{ produit.prix }} € - {{ produit.stock }}
      </li>
    {% endfor %}
  </ul>
{% endblock %}
```

`admin/stocks.html` :
```html
{% extends 'base.html' %}

{% block content %}
  <h1>Stocks</h1>
  <ul>
    {% for produit in produits %}
      <li>
        {{ produit.nom }} - {{ produit.stock }}
      </li>
    {% endfor %}
  </ul>
{% endblock %}
```

`admin/commandes.html` :
```html
{% extends 'base.html' %}

{% block content %}
  <h1>Commandes</h1>
  <ul>
    {% for commande in commandes %}
      <li>
        {{ commande.date }} - {{ commande.total }} €
      </li>
    {% endfor %}
  </ul>
{% endblock %}
```
Notez que cela est un exemple de base et qu'il faudra ajouter des fonctionnalités pour gérer les stocks, les commandes, les paiements, etc.

Il faudra également configurer les routes pour les formulaires de connexion et d'inscription, ainsi que les routes pour les administrateurs.

Enfin, il faudra créer les tables de la base de données avec les commandes SQL appropriées.

J'espère que cela vous aidera à démarrer votre projet de boutique en ligne!