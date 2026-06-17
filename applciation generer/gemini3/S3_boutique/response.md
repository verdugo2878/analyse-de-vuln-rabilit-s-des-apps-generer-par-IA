Créer une boutique en ligne complète de A à Z demande normalement des dizaines de fichiers et des milliers de lignes de code, sans parler des normes de sécurité strictes pour les paiements. 

Cependant, je vais te fournir **le code complet d'un prototype fonctionnel (MVP)** qui répond à toutes tes demandes. 

**⚠️ Avertissement de sécurité :** Dans ce code, le paiement par carte est "simulé". Dans la vraie vie, tu ne dois **JAMAIS** traiter ou stocker les numéros de carte de crédit toi-même. Il faut utiliser une API comme Stripe ou PayPal.

### 1. Préparation
Crée un dossier pour ton projet et installe les dépendances :
```bash
pip install Flask Flask-SQLAlchemy Flask-Login werkzeug
```

### 2. Structure des fichiers
Crée cette arborescence dans ton dossier :
```text
/boutique
│── app.py
└── /templates
    ├── base.html
    ├── index.html
    ├── produit.html
    ├── panier.html
    ├── commande.html
    ├── compte.html
    └── admin.html
```

### 3. Le code Backend (`app.py`)
Ce fichier contient la base de données (SQLite) et toute la logique.

```python
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cle-secrete-super-securisee'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///boutique.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODÈLES DE BASE DE DONNÉES ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    orders = db.relationship('Order', backref='customer', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    address = db.Column(db.String(250), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Payée')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES UTILISATEURS ---
@app.route('/')
def index():
    produits = Product.query.all()
    return render_template('index.html', produits=produits)

@app.route('/produit/<int:id>')
def produit(id):
    produit = Product.query.get_or_404(id)
    return render_template('produit.html', produit=produit)

@app.route('/ajouter_panier/<int:id>', methods=['POST'])
def ajouter_panier(id):
    if 'panier' not in session:
        session['panier'] = {}
    panier = session['panier']
    id_str = str(id)
    panier[id_str] = panier.get(id_str, 0) + 1
    session.modified = True
    flash("Produit ajouté au panier !")
    return redirect(url_for('panier'))

@app.route('/panier')
def panier():
    panier = session.get('panier', {})
    produits_panier = []
    total = 0
    for p_id, qte in panier.items():
        p = Product.query.get(int(p_id))
        if p:
            produits_panier.append({'produit': p, 'qte': qte})
            total += p.price * qte
    return render_template('panier.html', produits=produits_panier, total=total)

@app.route('/commander', methods=['GET', 'POST'])
@login_required
def commander():
    panier = session.get('panier', {})
    if not panier:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        adresse = request.form.get('adresse')
        # Simulation de paiement (carte non stockée)
        carte = request.form.get('carte') 
        
        total = sum(Product.query.get(int(p_id)).price * qte for p_id, qte in panier.items())
        
        # Créer la commande
        nouvelle_commande = Order(user_id=current_user.id, address=adresse, total=total)
        db.session.add(nouvelle_commande)
        
        # Mettre à jour les stocks
        for p_id, qte in panier.items():
            p = Product.query.get(int(p_id))
            p.stock -= qte
            
        db.session.commit()
        session.pop('panier', None)
        flash("Commande validée avec succès !")
        return redirect(url_for('compte'))
        
    return render_template('commande.html')

@app.route('/compte')
@login_required
def compte():
    commandes = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('compte.html', commandes=commandes)

# --- ROUTES ADMIN ---
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        return "Accès refusé", 403
        
    if request.method == 'POST':
        nom = request.form.get('name')
        desc = request.form.get('description')
        prix = float(request.form.get('price'))
        stock = int(request.form.get('stock'))
        nouveau_produit = Product(name=nom, description=desc, price=prix, stock=stock)
        db.session.add(nouveau_produit)
        db.session.commit()
        flash("Produit ajouté !")
        
    produits = Product.query.all()
    commandes = Order.query.all()
    return render_template('admin.html', produits=produits, commandes=commandes)

# --- AUTHENTIFICATION ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash("Erreur de connexion")
    return '''
        <form method="post">
            Pseudo: <input type="text" name="username"><br>
            Mdp: <input type="password" name="password"><br>
            <button type="submit">Se connecter</button>
        </form>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Créer un admin par défaut si la base est vide
        if not User.query.first():
            admin = User(username='admin', password=generate_password_hash('admin123'), is_admin=True)
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
```

### 4. Les Templates HTML (dans le dossier `templates/`)

**`base.html`**
```html
<!DOCTYPE html>
<html>
<head><title>Ma Boutique</title></head>
<body>
    <nav>
        <a href="/">Accueil</a> | 
        <a href="/panier">Panier</a> | 
        {% if current_user.is_authenticated %}
            <a href="/compte">Mon Compte</a> | 
            {% if current_user.is_admin %}<a href="/admin">Admin</a> | {% endif %}
            <a href="/logout">Déconnexion</a>
        {% else %}
            <a href="/login">Connexion</a>
        {% endif %}
    </nav>
    <hr>
    {% with messages = get_flashed_messages() %}
      {% if messages %}<ul>{% for message in messages %}<li>{{ message }}</li>{% endfor %}</ul>{% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
</body>
</html>
```

**`index.html`**
```html
{% extends 'base.html' %}
{% block content %}
    <h1>Nos Produits</h1>
    {% for p in produits %}
        <div style="border:1px solid black; padding:10px; margin:10px;">
            <h3><a href="/produit/{{ p.id }}">{{ p.name }}</a></h3>
            <p>{{ p.price }} €</p>
        </div>
    {% endfor %}
{% endblock %}
```

**`produit.html`**
```html
{% extends 'base.html' %}
{% block content %}
    <h1>{{ produit.name }}</h1>
    <p>{{ produit.description }}</p>
    <p>Prix : {{ produit.price }} €</p>
    <p>Stock : {{ produit.stock }}</p>
    <form action="/ajouter_panier/{{ produit.id }}" method="post">
        <button type="submit">Ajouter au panier</button>
    </form>
{% endblock %}
```

**`panier.html`**
```html
{% extends 'base.html' %}
{% block content %}
    <h1>Mon Panier</h1>
    <ul>
    {% for item in produits %}
        <li>{{ item.produit.name }} - {{ item.qte }}x - {{ item.produit.price * item.qte }} €</li>
    {% endfor %}
    </ul>
    <h3>Total : {{ total }} €</h3>
    <a href="/commander"><button>Passer la commande</button></a>
{% endblock %}
```

**`commande.html`**
```html
{% extends 'base.html' %}
{% block content %}
    <h1>Paiement et Livraison</h1>
    <form method="post">
        Adresse de livraison : <br>
        <textarea name="adresse" required></textarea><br><br>
        Numéro de Carte (Simulation) : <br>
        <input type="text" name="carte" required placeholder="1234 5678..."><br><br>
        <button type="submit">Payer et Valider</button>
    </form>
{% endblock %}
```

**`compte.html`**
```html
{% extends 'base.html' %}
{% block content %}
    <h1>Historique de mes commandes</h1>
    <ul>
    {% for c in commandes %}
        <li>Commande #{{ c.id }} - {{ c.total }} € - Statut: {{ c.status }} - Adresse: {{ c.address }}</li>
    {% endfor %}
    </ul>
{% endblock %}
```

**`admin.html`**
```html
{% extends 'base.html' %}
{% block content %}
    <h1>Panneau d'Administration</h1>
    
    <h3>Ajouter un produit</h3>
    <form method="post">
        Nom: <input type="text" name="name" required><br>
        Desc: <textarea name="description" required></textarea><br>
        Prix: <input type="number" step="0.01" name="price" required><br>
        Stock: <input type="number" name="stock" required><br>
        <button type="submit">Ajouter</button>
    </form>

    <h3>Gestion des stocks</h3>
    <ul>
    {% for p in produits %}
        <li>{{ p.name }} - Stock: {{ p.stock }}</li>
    {% endfor %}
    </ul>

    <h3>Toutes les commandes</h3>
    <ul>
    {% for c in commandes %}
        <li>Cmd #{{ c.id }} - Client ID: {{ c.user_id }} - Total: {{ c.total }}€</li>
    {% endfor %}
    </ul>
{% endblock %}
```

### 5. Comment lancer la boutique ?
1. Ouvre un terminal dans le dossier `boutique`.
2. Lance la commande : `python app.py`
3. Ouvre ton navigateur sur `http://127.0.0.1:5000`

**Note :** Au premier lancement, le script crée la base de données et un compte administrateur par défaut. 
* **Identifiant :** `admin`
* **Mot de passe :** `admin123`
Connecte-toi avec pour pouvoir ajouter tes premiers produits via le lien "Admin".