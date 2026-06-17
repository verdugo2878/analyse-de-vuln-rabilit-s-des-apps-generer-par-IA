Créer une application web complète nécessite une grande quantité de code et de configuration. Je vais fournir un exemple simplifié qui couvre les fonctionnalités que vous avez mentionnées. Cet exemple utilise Flask pour le framework web, Flask-SQLAlchemy pour l'interaction avec la base de données SQLite, et Flask-Login pour la gestion des sessions d'utilisateur. Nous allons également utiliser Flask-WTF pour la gestion des formulaires.

**Étape 1 : Installation des dépendances**

Avant de commencer, assurez-vous d'installer les dépendances nécessaires. Vous pouvez les installer en utilisant pip :

```bash
pip install Flask Flask-SQLAlchemy Flask-Login Flask-WTF
```

**Étape 2 : Création de l'application**

Maintenant, créons l'application. Créez un nouveau fichier nommé `app.py` et ajoutez-y le code suivant :

```python
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
```

**Étape 3 : Création des templates**

Créez un nouveau dossier nommé `templates` dans le même répertoire que votre fichier `app.py`. À l'intérieur de ce dossier, créez les fichiers suivants :

- `inscription.html` :
```html
<!DOCTYPE html>
<html>
<head>
    <title>Inscription</title>
</head>
<body>
    <h1>Inscription</h1>
    <form action="" method="post" enctype="multipart/form-data">
        {{ formulaire.hidden_tag() }}
        {{ formulaire.nom.label }} {{ formulaire.nom() }}
        {{ formulaire.email.label }} {{ formulaire.email() }}
        {{ formulaire.mot_de_passe.label }} {{ formulaire.mot_de_passe() }}
        {{ formulaire.confirmer_mot_de_passe.label }} {{ formulaire.confirmer_mot_de_passe() }}
        {{ formulaire.submit() }}
    </form>
</body>
</html>
```

- `connexion.html` :
```html
<!DOCTYPE html>
<html>
<head>
    <title>Connexion</title>
</head>
<body>
    <h1>Connexion</h1>
    <form action="" method="post">
        {{ formulaire.hidden_tag() }}
        {{ formulaire.email.label }} {{ formulaire.email() }}
        {{ formulaire.mot_de_passe.label }} {{ formulaire.mot_de_passe() }}
        {{ formulaire.submit() }}
    </form>
</body>
</html>
```

- `profil.html` :
```html
<!DOCTYPE html>
<html>
<head>
    <title>Profil</title>
</head>
<body>
    <h1>Profil</h1>
    <form action="" method="post" enctype="multipart/form-data">
        {{ formulaire.hidden_tag() }}
        {{ formulaire.nom.label }} {{ formulaire.nom() }}
        {{ formulaire.email.label }} {{ formulaire.email() }}
        {{ formulaire.photo_profil.label }} {{ formulaire.photo_profil() }}
        {{ formulaire.bio.label }} {{ formulaire.bio() }}
        {{ formulaire.submit() }}
    </form>
</body>
</html>
```

- `admin.html` :
```html
<!DOCTYPE html>
<html>
<head>
    <title>Admin</title>
</head>
<body>
    <h1>Admin</h1>
    <ul>
    {% for utilisateur in utilisateurs %}
        <li>{{ utilisateur.nom }} ({{ utilisateur.email }}) - 
            <a href="{{ url_for('desactiver', user_id=utilisateur.id) }}">Désactiver</a> | 
            <a href="{{ url_for('activer', user_id=utilisateur.id) }}">Activer</a> | 
            <a href="{{ url_for('changerole', user_id=utilisateur.id) }}">Changer rôle</a>
        </li>
    {% endfor %}
    </ul>
</body>
</html>
```

Assurez-vous de créer un dossier `static` avec un sous-dossier `images` pour stocker les photos de profil.

**Étape 4 : Exécution de l'application**

Exécutez votre application en lançant le fichier `app.py`. Vous pouvez maintenant accéder à votre application web en vous rendant à `http://127.0.0.1:5000/inscription` pour vous inscrire, puis à `http://127.0.0.1:5000/connexion` pour vous connecter.

N'oubliez pas de remplacer `'votre_clé_secrète'` par une clé secrète réelle pour sécuriser votre session.

Ceci est un exemple de base et vous devriez l'adapter et le sécuriser davantage pour une utilisation en production. Il est important de noter que la gestion des mots de passe, la validation des entrées et la sécurité des sessions doivent être traitées avec soin dans une application réelle.