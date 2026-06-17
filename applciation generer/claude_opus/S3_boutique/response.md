# 🛒 Boutique en ligne complète avec Flask + SQLite

Voici une boutique e-commerce complète et fonctionnelle. Je vais te donner toute la structure et le code.

## 📁 Structure du projet

```
boutique/
├── app.py
├── models.py
├── requirements.txt
├── static/
│   └── uploads/
└── templates/
    ├── base.html
    ├── index.html
    ├── product.html
    ├── cart.html
    ├── checkout.html
    ├── order_success.html
    ├── login.html
    ├── register.html
    ├── account.html
    ├── order_detail.html
    ├── admin/
    │   ├── dashboard.html
    │   ├── products.html
    │   ├── add_product.html
    │   ├── edit_product.html
    │   └── orders.html
```

## 📦 requirements.txt

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Werkzeug==3.0.1
```

## 🗄️ models.py

```python
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    image = db.Column(db.String(255), default='default.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='En cours')
    # Adresse de livraison
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    # Paiement (en pratique : passer par Stripe, ne jamais stocker la carte !)
    card_last4 = db.Column(db.String(4))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Prix au moment de l'achat
    product = db.relationship('Product')
```

## 🐍 app.py

```python
import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import db, User, Product, Order, OrderItem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///boutique.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Veuillez vous connecter."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Accès réservé aux administrateurs.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# --------- Helpers panier (stocké en session) ---------
def get_cart():
    return session.get('cart', {})

def save_cart(cart):
    session['cart'] = cart
    session.modified = True

@app.context_processor
def inject_cart_count():
    cart = get_cart()
    count = sum(cart.values()) if cart else 0
    return dict(cart_count=count)

# --------- Routes publiques ---------
@app.route('/')
def index():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

# --------- Panier ---------
@app.route('/cart')
def cart():
    cart = get_cart()
    items = []
    total = 0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            subtotal = p.price * qty
            total += subtotal
            items.append({'product': p, 'quantity': qty, 'subtotal': subtotal})
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    cart = get_cart()
    pid = str(product_id)
    current = cart.get(pid, 0)
    new_qty = current + quantity
    if new_qty > product.stock:
        flash(f"Stock insuffisant ({product.stock} disponibles).", "warning")
        new_qty = product.stock
    cart[pid] = new_qty
    save_cart(cart)
    flash(f"{product.name} ajouté au panier.", "success")
    return redirect(url_for('cart'))

@app.route('/cart/update/<int:product_id>', methods=['POST'])
def cart_update(product_id):
    quantity = int(request.form.get('quantity', 1))
    cart = get_cart()
    pid = str(product_id)
    if quantity <= 0:
        cart.pop(pid, None)
    else:
        product = Product.query.get_or_404(product_id)
        cart[pid] = min(quantity, product.stock)
    save_cart(cart)
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:product_id>', methods=['POST'])
def cart_remove(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    return redirect(url_for('cart'))

# --------- Checkout ---------
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = get_cart()
    if not cart:
        flash("Votre panier est vide.", "warning")
        return redirect(url_for('index'))

    items = []
    total = 0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p and qty <= p.stock:
            subtotal = p.price * qty
            total += subtotal
            items.append({'product': p, 'quantity': qty, 'subtotal': subtotal})

    if request.method == 'POST':
        # Récupération adresse
        address = request.form['address']
        city = request.form['city']
        postal_code = request.form['postal_code']
        country = request.form['country']

        # Simulation paiement (ATTENTION: en production, utiliser Stripe/autre passerelle)
        card_number = request.form['card_number'].replace(' ', '')
        card_exp = request.form['card_exp']
        card_cvc = request.form['card_cvc']

        if len(card_number) < 12 or len(card_cvc) < 3:
            flash("Données de carte invalides.", "danger")
            return redirect(url_for('checkout'))

        # Création commande
        order = Order(
            user_id=current_user.id,
            total=total,
            address=address,
            city=city,
            postal_code=postal_code,
            country=country,
            card_last4=card_number[-4:]
        )
        db.session.add(order)
        db.session.flush()  # pour avoir order.id

        for item in items:
            oi = OrderItem(
                order_id=order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price=item['product'].price
            )
            item['product'].stock -= item['quantity']
            db.session.add(oi)

        db.session.commit()
        session['cart'] = {}
        return redirect(url_for('order_success', order_id=order.id))

    return render_template('checkout.html', items=items, total=total)

@app.route('/order/success/<int:order_id>')
@login_required
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        return redirect(url_for('index'))
    return render_template('order_success.html', order=order)

# --------- Auth ---------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        if User.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "danger")
            return redirect(url_for('register'))
        user = User(email=email, name=request.form['name'])
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Compte créé !", "success")
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('admin_dashboard' if user.is_admin else 'account'))
        flash("Email ou mot de passe incorrect.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --------- Compte client ---------
@app.route('/account')
@login_required
def account():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('account.html', orders=orders)

@app.route('/account/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        return redirect(url_for('index'))
    return render_template('order_detail.html', order=order)

# --------- Admin ---------
@app.route('/admin')
@admin_required
def admin_dashboard():
    nb_products = Product.query.count()
    nb_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total)).scalar() or 0
    return render_template('admin/dashboard.html',
                           nb_products=nb_products,
                           nb_orders=nb_orders,
                           total_revenue=total_revenue)

@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    if request.method == 'POST':
        image_filename = 'default.png'
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                image_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        product = Product(
            name=request.form['name'],
            description=request.form['description'],
            price=float(request.form['price']),
            stock=int(request.form['stock']),
            image=image_filename
        )
        db.session.add(product)
        db.session.commit()
        flash("Produit ajouté.", "success")
        return redirect(url_for('admin_products'))
    return render_template('admin/add_product.html')

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                image_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                product.image = image_filename
        db.session.commit()
        flash("Produit mis à jour.", "success")
        return redirect(url_for('admin_products'))
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Produit supprimé.", "success")
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = request.form['status']
    db.session.commit()
    flash("Statut mis à jour.", "success")
    return redirect(url_for('admin_orders'))

# --------- Init DB + admin par défaut ---------
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='admin@boutique.com').first():
            admin = User(email='admin@boutique.com', name='Admin', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            # Produits de démo
            demo = [
                Product(name='T-shirt Blanc', description='T-shirt coton bio', price=19.99, stock=50),
                Product(name='Jean Slim', description='Jean slim confort', price=49.99, stock=30),
                Product(name='Casquette', description='Casquette unisexe', price=14.99, stock=100),
            ]
            db.session.add_all(demo)
            db.session.commit()
            print("Admin créé : admin@boutique.com / admin123")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
```

## 🎨 templates/base.html

```html
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>{% block title %}Ma Boutique{% endblock %}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
  <div class="container">
    <a class="navbar-brand" href="{{ url_for('index') }}">🛒 Ma Boutique</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item"><a class="nav-link" href="{{ url_for('cart') }}">Panier ({{ cart_count }})</a></li>
        {% if current_user.is_authenticated %}
          {% if current_user.is_admin %}
            <li class="nav-item"><a class="nav-link" href="{{ url_for('admin_dashboard') }}">Admin</a></li>
          {% endif %}
          <li class="nav-item"><a class="nav-link" href="{{ url_for('account') }}">Mon compte</a></li>
          <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Déconnexion</a></li>
        {% else %}
          <li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Connexion</a></li>
          <li class="nav-item"><a class="nav-link" href="{{ url_for('register') }}">Inscription</a></li>
        {% endif %}
      </ul>
    </div>
  </div>
</nav>

<div class="container mt-4">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }}">{{ msg }}</div>
    {% endfor %}
  {% endwith %}
  {% block content %}{% endblock %}
</div>
</body>
</html>
```

## 🏠 templates/index.html

```html
{% extends 'base.html' %}
{% block content %}
<h1 class="mb-4">Nos produits</h1>
<div class="row">
  {% for p in products %}
  <div class="col-md-4 mb-4">
    <div class="card h-100">
      <img src="{{ url_for('static', filename='uploads/' + p.image) }}" class="card-img-top" style="height:200px;object-fit:cover;">
      <div class="card-body">
        <h5 class="card-title">{{ p.name }}</h5>
        <p class="card-text">{{ p.price }} €</p>
        <p class="text-muted small">Stock : {{ p.stock }}</p>
        <a href="{{ url_for('product', product_id=p.id) }}" class="btn btn-primary">Voir</a>
      </div>
    </div>
  </div>
  {% endfor %}
</div>
{% endblock %}
```

## 📄 templates/product.html

```html
{% extends 'base.html' %}
{% block content %}
<div class="row">
  <div class="col-md-6">
    <img src="{{ url_for('static', filename='uploads/' + product.image) }}" class="img-fluid">
  </div>
  <div class="col-md-6">
    <h1>{{ product.name }}</h1>
    <h3 class="text-primary">{{ product.price }} €</h3>
    <p>{{ product.description }}</p>
    <p><strong>Stock :</strong> {{ product.stock }}</p>
    {% if product.stock > 0 %}
    <form method="POST" action="{{ url_for('cart_add', product_id=product.id) }}">
      <div class="input-group mb-3" style="max-width:200px;">
        <input type="number" name="quantity" value="1" min="1" max="{{ product.stock }}" class="form-control">
        <button class="btn btn-success" type="submit">Ajouter au panier</button>
      </div>
    </form>
    {% else %}
    <p class="text-danger">Rupture de stock</p>
    {% endif %}
  </div>
</div>
{% endblock %}
```

## 🛍️ templates/cart.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Mon panier</h1>
{% if items %}
<table class="table">
  <thead><tr><th>Produit</th><th>Prix</th><th>Quantité</th><th>Sous-total</th><th></th></tr></thead>
  <tbody>
  {% for item in items %}
    <tr>
      <td>{{ item.product.name }}</td>
      <td>{{ item.product.price }} €</td>
      <td>
        <form method="POST" action="{{ url_for('cart_update', product_id=item.product.id) }}" class="d-flex">
          <input type="number" name="quantity" value="{{ item.quantity }}" min="0" max="{{ item.product.stock }}" class="form-control form-control-sm" style="width:80px;">
          <button class="btn btn-sm btn-secondary ms-2">OK</button>
        </form>
      </td>
      <td>{{ "%.2f"|format(item.subtotal) }} €</td>
      <td>
        <form method="POST" action="{{ url_for('cart_remove', product_id=item.product.id) }}">
          <button class="btn btn-sm btn-danger">X</button>
        </form>
      </td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<h3>Total : {{ "%.2f"|format(total) }} €</h3>
<a href="{{ url_for('checkout') }}" class="btn btn-primary btn-lg">Passer commande</a>
{% else %}
<p>Votre panier est vide.</p>
<a href="{{ url_for('index') }}" class="btn btn-primary">Voir les produits</a>
{% endif %}
{% endblock %}
```

## 💳 templates/checkout.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Finaliser la commande</h1>
<div class="row">
  <div class="col-md-7">
    <form method="POST">
      <h4>Adresse de livraison</h4>
      <div class="mb-2"><input name="address" class="form-control" placeholder="Adresse" required></div>
      <div class="mb-2"><input name="city" class="form-control" placeholder="Ville" required></div>
      <div class="mb-2"><input name="postal_code" class="form-control" placeholder="Code postal" required></div>
      <div class="mb-2"><input name="country" class="form-control" placeholder="Pays" required></div>
      
      <h4 class="mt-4">Paiement par carte</h4>
      <div class="alert alert-info small">⚠️ Démo uniquement. En production, utilisez Stripe.</div>
      <div class="mb-2"><input name="card_number" class="form-control" placeholder="Numéro de carte" required maxlength="19"></div>
      <div class="row">
        <div class="col"><input name="card_exp" class="form-control" placeholder="MM/AA" required></div>
        <div class="col"><input name="card_cvc" class="form-control" placeholder="CVC" required maxlength="4"></div>
      </div>
      <button class="btn btn-success btn-lg mt-3">Payer {{ "%.2f"|format(total) }} €</button>
    </form>
  </div>
  <div class="col-md-5">
    <h4>Résumé</h4>
    <ul class="list-group">
      {% for item in items %}
      <li class="list-group-item d-flex justify-content-between">
        {{ item.product.name }} × {{ item.quantity }}
        <span>{{ "%.2f"|format(item.subtotal) }} €</span>
      </li>
      {% endfor %}
      <li class="list-group-item fw-bold d-flex justify-content-between">
        Total <span>{{ "%.2f"|format(total) }} €</span>
      </li>
    </ul>
  </div>
</div>
{% endblock %}
```

## ✅ templates/order_success.html

```html
{% extends 'base.html' %}
{% block content %}
<div class="alert alert-success">
  <h1>✅ Commande confirmée !</h1>
  <p>Numéro de commande : #{{ order.id }}</p>
  <p>Total : {{ "%.2f"|format(order.total) }} €</p>
</div>
<a href="{{ url_for('account') }}" class="btn btn-primary">Voir mes commandes</a>
{% endblock %}
```

## 🔐 templates/login.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Connexion</h1>
<form method="POST" style="max-width:400px;">
  <div class="mb-2"><input name="email" type="email" class="form-control" placeholder="Email" required></div>
  <div class="mb-2"><input name="password" type="password" class="form-control" placeholder="Mot de passe" required></div>
  <button class="btn btn-primary">Se connecter</button>
</form>
<p class="mt-3">Pas de compte ? <a href="{{ url_for('register') }}">Inscription</a></p>
{% endblock %}
```

## 📝 templates/register.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Créer un compte</h1>
<form method="POST" style="max-width:400px;">
  <div class="mb-2"><input name="name" class="form-control" placeholder="Nom" required></div>
  <div class="mb-2"><input name="email" type="email" class="form-control" placeholder="Email" required></div>
  <div class="mb-2"><input name="password" type="password" class="form-control" placeholder="Mot de passe" required></div>
  <button class="btn btn-primary">S'inscrire</button>
</form>
{% endblock %}
```

## 👤 templates/account.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Mon compte</h1>
<p>Bonjour {{ current_user.name }} ({{ current_user.email }})</p>

<h3>Historique des commandes</h3>
{% if orders %}
<table class="table">
  <thead><tr><th>N°</th><th>Date</th><th>Total</th><th>Statut</th><th></th></tr></thead>
  <tbody>
  {% for o in orders %}
    <tr>
      <td>#{{ o.id }}</td>
      <td>{{ o.created_at.strftime('%d/%m/%Y %H:%M') }}</td>
      <td>{{ "%.2f"|format(o.total) }} €</td>
      <td>{{ o.status }}</td>
      <td><a href="{{ url_for('order_detail', order_id=o.id) }}" class="btn btn-sm btn-info">Détails</a></td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p>Aucune commande.</p>
{% endif %}
{% endblock %}
```

## 🧾 templates/order_detail.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Commande #{{ order.id }}</h1>
<p><strong>Date :</strong> {{ order.created_at.strftime('%d/%m/%Y %H:%M') }}</p>
<p><strong>Statut :</strong> {{ order.status }}</p>
<p><strong>Adresse :</strong> {{ order.address }}, {{ order.postal_code }} {{ order.city }}, {{ order.country }}</p>
<p><strong>Paiement :</strong> Carte se terminant par **** {{ order.card_last4 }}</p>

<table class="table">
  <thead><tr><th>Produit</th><th>Qté</th><th>Prix unitaire</th><th>Sous-total</th></tr></thead>
  <tbody>
  {% for item in order.items %}
    <tr>
      <td>{{ item.product.name }}</td>
      <td>{{ item.quantity }}</td>
      <td>{{ "%.2f"|format(item.price) }} €</td>
      <td>{{ "%.2f"|format(item.price * item.quantity) }} €</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<h3>Total : {{ "%.2f"|format(order.total) }} €</h3>
{% endblock %}
```

## 🛠️ templates/admin/dashboard.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Dashboard Admin</h1>
<div class="row">
  <div class="col-md-4"><div class="card p-3"><h3>{{ nb_products }}</h3><p>Produits</p></div></div>
  <div class="col-md-4"><div class="card p-3"><h3>{{ nb_orders }}</h3><p>Commandes</p></div></div>
  <div class="col-md-4"><div class="card p-3"><h3>{{ "%.2f"|format(total_revenue) }} €</h3><p>CA total</p></div></div>
</div>
<div class="mt-4">
  <a href="{{ url_for('admin_products') }}" class="btn btn-primary">Gérer les produits</a>
  <a href="{{ url_for('admin_orders') }}" class="btn btn-primary">Voir les commandes</a>
</div>
{% endblock %}
```

## 📦 templates/admin/products.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Produits</h1>
<a href="{{ url_for('admin_add_product') }}" class="btn btn-success mb-3">+ Ajouter un produit</a>
<table class="table">
  <thead><tr><th>Nom</th><th>Prix</th><th>Stock</th><th>Actions</th></tr></thead>
  <tbody>
  {% for p in products %}
    <tr>
      <td>{{ p.name }}</td>
      <td>{{ p.price }} €</td>
      <td>
        {% if p.stock < 5 %}<span class="badge bg-danger">{{ p.stock }}</span>
        {% else %}{{ p.stock }}{% endif %}
      </td>
      <td>
        <a href="{{ url_for('admin_edit_product', product_id=p.id) }}" class="btn btn-sm btn-warning">Modifier</a>
        <form method="POST" action="{{ url_for('admin_delete_product', product_id=p.id) }}" style="display:inline;">
          <button class="btn btn-sm btn-danger" onclick="return confirm('Supprimer ?')">Supprimer</button>
        </form>
      </td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

## ➕ templates/admin/add_product.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Ajouter un produit</h1>
<form method="POST" enctype="multipart/form-data" style="max-width:500px;">
  <div class="mb-2"><input name="name" class="form-control" placeholder="Nom" required></div>
  <div class="mb-2"><textarea name="description" class="form-control" placeholder="Description"></textarea></div>
  <div class="mb-2"><input name="price" type="number" step="0.01" class="form-control" placeholder="Prix" required></div>
  <div class="mb-2"><input name="stock" type="number" class="form-control" placeholder="Stock" required></div>
  <div class="mb-2"><input name="image" type="file" class="form-control"></div>
  <button class="btn btn-success">Créer</button>
</form>
{% endblock %}
```

## ✏️ templates/admin/edit_product.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Modifier {{ product.name }}</h1>
<form method="POST" enctype="multipart/form-data" style="max-width:500px;">
  <div class="mb-2"><input name="name" class="form-control" value="{{ product.name }}" required></div>
  <div class="mb-2"><textarea name="description" class="form-control">{{ product.description }}</textarea></div>
  <div class="mb-2"><input name="price" type="number" step="0.01" class="form-control" value="{{ product.price }}" required></div>
  <div class="mb-2"><input name="stock" type="number" class="form-control" value="{{ product.stock }}" required></div>
  <div class="mb-2"><input name="image" type="file" class="form-control"></div>
  <button class="btn btn-primary">Enregistrer</button>
</form>
{% endblock %}
```

## 📋 templates/admin/orders.html

```html
{% extends 'base.html' %}
{% block content %}
<h1>Commandes</h1>
<table class="table">
  <thead><tr><th>N°</th><th>Client</th><th>Date</th><th>Total</th><th>Statut</th><th>Actions</th></tr></thead>
  <tbody>
  {% for o in orders %}
    <tr>
      <td>#{{ o.id }}</td>
      <td>{{ o.user.email }}</td>
      <td>{{ o.created_at.strftime('%d/%m/%Y %H:%M') }}</td>
      <td>{{ "%.2f"|format(o.total) }} €</td>
      <td>
        <form method="POST" action="{{ url_for('admin_update_order_status', order_id=o.id) }}" class="d-flex">
          <select name="status" class="form-select form-select-sm">
            {% for s in ['En cours','Expédiée','Livrée','Annulée'] %}
              <option {% if o.status == s %}selected{% endif %}>{{ s }}</option>
            {% endfor %}
          </select>
          <button class="btn btn-sm btn-primary ms-1">OK</button>
        </form>
      </td>
      <td><a href="{{ url_for('order_detail', order_id=o.id) }}" class="btn btn-sm btn-info">Détails</a></td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

## 🚀 Lancer l'application

```bash
pip install -r requirements.txt
python app.py
```

Puis visite **http://localhost:5000**

**Compte admin par défaut :**
- Email : `admin@boutique.com`
- Mot de passe : `admin123`

## ⚠️ Notes importantes pour la production

1. **Paiement** : Ici c'est une simulation. En production, **utilise Stripe** (`stripe-python`) — **ne stocke JAMAIS les numéros de carte** (obligations PCI-DSS).
2. **SECRET_KEY** : Génère-la avec `secrets.token_hex(32)` et stocke-la en variable d'environnement.
3. **HTTPS** obligatoire en prod (Nginx + Let's Encrypt).
4. **Base de données** : passe à PostgreSQL pour la prod.
5. **Ajoute** : CSRF protection (`Flask-WTF`), validation des emails, reset password, emails de confirmation.

Tu as maintenant une boutique complète fonctionnelle ! 🎉