Je vais créer une boutique en ligne complète avec Flask et SQLite. Voici l'ensemble du code structuré en plusieurs fichiers.

## Structure du projet :
```
boutique_en_ligne/
│
├── app.py
├── database.py
├── models.py
├── requirements.txt
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── product.html
│   ├── cart.html
│   ├── checkout.html
│   ├── order_confirmation.html
│   ├── login.html
│   ├── register.html
│   ├── account.html
│   ├── admin.html
│   ├── admin_products.html
│   ├── admin_orders.html
│   └── admin_add_product.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── images/
│
└── instance/
    └── boutique.db
```

## 1. requirements.txt
```txt
Flask==2.3.3
Flask-Login==0.6.2
Flask-Bcrypt==1.0.1
```

## 2. database.py
```python
import sqlite3
from flask import g
import os

DATABASE = os.path.join(os.path.dirname(__file__), 'instance', 'boutique.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    
    # Création des tables
    with open('schema.sql', 'r') as f:
        db.executescript(f.read())
    db.commit()

def init_app(app):
    app.teardown_appcontext(close_db)
```

## 3. models.py
```python
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

class User(UserMixin):
    def __init__(self, id, email, password, is_admin=False):
        self.id = id
        self.email = email
        self.password = password
        self.is_admin = is_admin

    @staticmethod
    def get(user_id):
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return None
        return User(id=user['id'], email=user['email'], password=user['password'], is_admin=bool(user['is_admin']))

    @staticmethod
    def get_by_email(email):
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not user:
            return None
        return User(id=user['id'], email=user['email'], password=user['password'], is_admin=bool(user['is_admin']))

class Product:
    def __init__(self, id, name, description, price, stock, image_url=None):
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.stock = stock
        self.image_url = image_url

    @staticmethod
    def get_all():
        db = get_db()
        products = db.execute('SELECT * FROM products').fetchall()
        return [Product(id=p['id'], name=p['name'], description=p['description'], 
                       price=p['price'], stock=p['stock'], image_url=p['image_url']) for p in products]

    @staticmethod
    def get_by_id(product_id):
        db = get_db()
        product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        if not product:
            return None
        return Product(id=product['id'], name=product['name'], description=product['description'],
                      price=product['price'], stock=product['stock'], image_url=product['image_url'])

class Order:
    def __init__(self, id, user_id, total, status, created_at, shipping_address):
        self.id = id
        self.user_id = user_id
        self.total = total
        self.status = status
        self.created_at = created_at
        self.shipping_address = shipping_address

    @staticmethod
    def get_by_user(user_id):
        db = get_db()
        orders = db.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
        return [Order(id=o['id'], user_id=o['user_id'], total=o['total'], 
                     status=o['status'], created_at=o['created_at'], 
                     shipping_address=o['shipping_address']) for o in orders]

    @staticmethod
    def get_all():
        db = get_db()
        orders = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
        return [Order(id=o['id'], user_id=o['user_id'], total=o['total'],
                     status=o['status'], created_at=o['created_at'],
                     shipping_address=o['shipping_address']) for o in orders]
```

## 4. schema.sql (fichier à créer)
```sql
-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des produits
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    stock INTEGER NOT NULL,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des commandes
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    shipping_address TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Table des éléments de commande
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders (id),
    FOREIGN KEY (product_id) REFERENCES products (id)
);

-- Table du panier (session-based)
CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products (id)
);

-- Insérer un admin par défaut (mot de passe: admin123)
INSERT OR IGNORE INTO users (email, password, is_admin) 
VALUES ('admin@boutique.com', 'scrypt:32768:8:1$zYfX7T0i$c29a6c5e8f7d4b3a2c1b0a9f8e7d6c5b4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0', 1);

-- Insérer quelques produits d'exemple
INSERT OR IGNORE INTO products (name, description, price, stock, image_url) VALUES
('T-shirt Blanc', 'T-shirt en coton 100% de haute qualité', 19.99, 50, '/static/images/tshirt.jpg'),
('Jeans Slim', 'Jeans slim fit délavé', 49.99, 30, '/static/images/jeans.jpg'),
('Chaussures de Sport', 'Chaussures de sport confortables', 79.99, 20, '/static/images/shoes.jpg'),
('Sac à dos', 'Sac à dos waterproof 30L', 39.99, 40, '/static/images/backpack.jpg'),
('Montre Connectée', 'Montre connectée avec suivi d''activité', 129.99, 15, '/static/images/watch.jpg');
```

## 5. app.py (principal)
```python
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime

from database import get_db, init_app
from models import User, Product, Order

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_clé_secrète_très_sécurisée'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Initialiser Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialiser la base de données
init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Fonction pour obtenir l'ID de session
def get_session_id():
    if not session.get('session_id'):
        session['session_id'] = os.urandom(16).hex()
    return session['session_id']

# Routes principales
@app.route('/')
def index():
    products = Product.get_all()
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.get_by_id(product_id)
    if not product:
        flash('Produit non trouvé', 'error')
        return redirect(url_for('index'))
    return render_template('product.html', product=product)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    product = Product.get_by_id(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Produit non trouvé'})
    
    if quantity > product.stock:
        return jsonify({'success': False, 'message': 'Stock insuffisant'})
    
    session_id = get_session_id()
    db = get_db()
    
    # Vérifier si le produit est déjà dans le panier
    existing_item = db.execute(
        'SELECT * FROM cart_items WHERE session_id = ? AND product_id = ?',
        (session_id, product_id)
    ).fetchone()
    
    if existing_item:
        new_quantity = existing_item['quantity'] + quantity
        db.execute(
            'UPDATE cart_items SET quantity = ? WHERE id = ?',
            (new_quantity, existing_item['id'])
        )
    else:
        db.execute(
            'INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)',
            (session_id, product_id, quantity)
        )
    
    db.commit()
    return jsonify({'success': True, 'message': 'Produit ajouté au panier'})

@app.route('/cart')
def cart():
    session_id = get_session_id()
    db = get_db()
    
    cart_items = db.execute('''
        SELECT ci.*, p.name, p.price, p.image_url, p.stock 
        FROM cart_items ci 
        JOIN products p ON ci.product_id = p.id 
        WHERE ci.session_id = ?
    ''', (session_id,)).fetchall()
    
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart', methods=['POST'])
def update_cart():
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))
    
    db = get_db()
    
    # Vérifier le stock
    cart_item = db.execute('''
        SELECT ci.*, p.stock 
        FROM cart_items ci 
        JOIN products p ON ci.product_id = p.id 
        WHERE ci.id = ?
    ''', (item_id,)).fetchone()
    
    if not cart_item:
        return jsonify({'success': False, 'message': 'Élément non trouvé'})
    
    if quantity > cart_item['stock']:
        return jsonify({'success': False, 'message': 'Stock insuffisant'})
    
    if quantity <= 0:
        db.execute('DELETE FROM cart_items WHERE id = ?', (item_id,))
    else:
        db.execute('UPDATE cart_items SET quantity = ? WHERE id = ?', (quantity, item_id))
    
    db.commit()
    return jsonify({'success': True})

@app.route('/remove_from_cart/<int:item_id>')
def remove_from_cart(item_id):
    db = get_db()
    db.execute('DELETE FROM cart_items WHERE id = ?', (item_id,))
    db.commit()
    flash('Produit retiré du panier', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    session_id = get_session_id()
    db = get_db()
    
    cart_items = db.execute('''
        SELECT ci.*, p.name, p.price, p.image_url 
        FROM cart_items ci 
        JOIN products p ON ci.product_id = p.id 
        WHERE ci.session_id = ?
    ''', (session_id,)).fetchall()
    
    if not cart_items:
        flash('Votre panier est vide', 'error')
        return redirect(url_for('cart'))
    
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    shipping_address = request.form.get('shipping_address')
    card_number = request.form.get('card_number')
    card_expiry = request.form.get('card_expiry')
    card_cvv = request.form.get('card_cvv')
    
    # Validation simplifiée du paiement
    if not all([shipping_address, card_number, card_expiry, card_cvv]):
        flash('Veuillez remplir tous les champs', 'error')
        return redirect(url_for('checkout'))
    
    session_id = get_session_id()
    db = get_db()
    
    # Récupérer les articles du panier
    cart_items = db.execute('''
        SELECT ci.*, p.price, p.stock 
        FROM cart_items ci 
        JOIN products p ON ci.product_id = p.id 
        WHERE ci.session_id = ?
    ''', (session_id,)).fetchall()
    
    if not cart_items:
        flash('Votre panier est vide', 'error')
        return redirect(url_for('cart'))
    
    # Calculer le total
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Vérifier le stock
    for item in cart_items:
        if item['quantity'] > item['stock']:
            flash(f'Stock insuffisant pour {item["name"]}', 'error')
            return redirect(url_for('cart'))
    
    # Créer la commande
    cursor = db.execute(
        'INSERT INTO orders (user_id, total, shipping_address) VALUES (?, ?, ?)',
        (current_user.id, total, shipping_address)
    )
    order_id = cursor.lastrowid
    
    # Ajouter les articles de la commande et mettre à jour le stock
    for item in cart_items:
        db.execute(
            'INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)',
            (order_id, item['product_id'], item['quantity'], item['price'])
        )
        
        # Mettre à jour le stock
        db.execute(
            'UPDATE products SET stock = stock - ? WHERE id = ?',
            (item['quantity'], item['product_id'])
        )
    
    # Vider le panier
    db.execute('DELETE FROM cart_items WHERE session_id = ?', (session_id,))
    
    db.commit()
    
    # Simuler le paiement (dans une vraie application, utiliser Stripe, PayPal, etc.)
    # Ici, nous simulons simplement un paiement réussi
    
    return render_template('order_confirmation.html', order_id=order_id, total=total)

# Authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.get_by_email(email)
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Connexion réussie!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email ou mot de passe incorrect', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'error')
            return render_template('register.html')
        
        db = get_db()
        
        # Vérifier si l'email existe déjà
        existing_user = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            flash('Cet email est déjà utilisé', 'error')
            return render_template('register.html')
        
        # Créer l'utilisateur
        hashed_password = generate_password_hash(password)
        db.execute(
            'INSERT INTO users (email, password) VALUES (?, ?)',
            (email, hashed_password)
        )
        db.commit()
        
        flash('Compte créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté', 'success')
    return redirect(url_for('index'))

# Compte client
@app.route('/account')
@login_required
def account():
    orders = Order.get_by_user(current_user.id)
    return render_template('account.html', orders=orders)

# Administration
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    db = get_db()
    
    # Statistiques
    total_products = db.execute('SELECT COUNT(*) as count FROM products').fetchone()['count']
    total_orders = db.execute('SELECT COUNT(*) as count FROM orders').fetchone()['count']
    total_users = db.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    
    # Dernières commandes
    recent_orders = db.execute('''
        SELECT o.*, u.email 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        ORDER BY o.created_at DESC 
        LIMIT 5
    ''').fetchall()
    
    return render_template('admin.html', 
                         total_products=total_products,
                         total_orders=total_orders,
                         total_users=total_users,
                         recent_orders=recent_orders)

@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    products = Product.get_all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/add_product', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    if not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        stock = int(request.form.get('stock'))
        
        # Gestion de l'image
        image_url = None
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = f'/static/images/{filename}'
        
        db = get_db()
        db.execute(
            'INSERT INTO products (name, description, price, stock, image_url) VALUES (?, ?, ?, ?, ?)',
            (name, description, price, stock, image_url)
        )
        db.commit()
        
        flash('Produit ajouté avec succès', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin_add_product.html')

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(product_id):
    if not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if not product:
        flash('Produit non trouvé', 'error')
        return redirect(url_for('admin_products'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        stock = int(request.form.get('stock'))
        
        # Gestion de l'image
        image_url = product['image_url']
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = f'/static/images/{filename}'
        
        db.execute(
            'UPDATE products SET name = ?, description = ?, price = ?, stock = ?, image_url = ? WHERE id = ?',
            (name, description, price, stock, image_url, product_id)
        )
        db.commit()
        
        flash('Produit mis à jour avec succès', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin_edit_product.html', product=product)

@app.route('/admin/delete_product/<int:product_id>')
@login_required
def admin_delete_product(product_id):
    if not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    db = get_db()
    db.execute('DELETE FROM products WHERE id = ?', (product_id,))
    db.commit()
    
    flash('Produit supprimé avec succès', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    orders = Order.get_all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/order/<int:order_id>')
@login_required
def admin_order_detail(order_id):
    if not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    
    db = get_db()
    
    order = db.execute('''
        SELECT o.*, u.email 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        WHERE o.id = ?
    ''', (order_id,)).fetchone()
    
    if not order:
        flash('Commande non trouvée', 'error')
        return redirect(url_for('admin_orders'))
    
    order_items = db.execute('''
        SELECT oi.*, p.name 
        FROM order_items oi 
        JOIN products p ON oi.product_id = p.id 
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    
    return render_template('admin_order_detail.html', order=order, order_items=order_items)

@app.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accès non autorisé'})
    
    status = request.form.get('status')
    
    db = get_db()
    db.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    db.commit()
    
    return jsonify({'success': True, 'message': 'Statut mis à jour'})

# API pour le panier
@app.route('/api/cart_count')
def cart_count():
    session_id = get_session_id()
    db = get_db()
    
    count = db.execute('SELECT SUM(quantity) as total FROM cart_items WHERE session_id = ?', 
                      (session_id,)).fetchone()
    
    return jsonify({'count': count['total'] or 0})

if __name__ == '__main__':
    # Créer le dossier d'upload s'il n'existe pas
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialiser la base de données
    with app.app_context():
        db = get_db()
        # Exécuter le schéma SQL
        with open('schema.sql', 'r') as f:
            db.executescript(f.read())
        db.commit()
    
    app.run(debug=True, port=5000)
```

## 6. Templates HTML

### base.html
```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Boutique en ligne{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">Ma Boutique</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}">Accueil</a>
                    </li>
                    {% if current_user.is_authenticated and current_user.is_admin %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('admin') }}">Admin</a>
                    </li>
                    {% endif %}
                </ul>
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('cart') }}">
                            <i class="fas fa-shopping-cart"></i>
                            <span id="cart-count" class="badge bg-primary">0</span>
                        </a>
                    </li>
                    {% if current_user.is_authenticated %}
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown">
                            {{ current_user.email }}
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="{{ url_for('account') }}">Mon compte</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{{ url_for('logout') }}">Déconnexion</a></li>
                        </ul>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('login') }}">Connexion</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('register') }}">Inscription</a>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category if category != 'error' else 'danger' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <footer class="bg-dark text-white mt-5 py-4">
        <div class="container text-center">
            <p>&copy; 2024 Ma Boutique. Tous droits réservés.</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script>
        // Mettre à jour le nombre d'articles dans le panier
        function updateCartCount() {
            $.get('/api/cart_count', function(data) {
                $('#cart-count').text(data.count);
            });
        }
        
        $(document).ready(function() {
            updateCartCount();
        });
    </script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### index.html
```html
{% extends "base.html" %}

{% block title %}Accueil - Ma Boutique{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col-12">
        <h1>Nos Produits</h1>
        <p class="lead">Découvrez notre sélection exclusive</p>
    </div>
</div>

<div class="row">
    {% for product in products %}
    <div class="col-md-4 mb-4">
        <div class="card h-100">
            {% if product.image_url %}
            <img src="{{ product.image_url }}" class="card-img-top" alt="{{ product.name }}" style="height: 200px; object-fit: cover;">
            {% else %}
            <div class="card-img-top bg-secondary d-flex align-items-center justify-content-center" style="height: 200px;">
                <i class="fas fa-image fa-3x text-white"></i>
            </div>
            {% endif %}
            <div class="card-body d-flex flex-column">
                <h5 class="card-title">{{ product.name }}</h5>
                <p class="card-text">{{ product.description[:100] }}{% if product.description|length > 100 %}...{% endif %}</p>
                <div class="mt-auto">
                    <p class="card-text"><strong>{{ product.price }} €</strong></p>
                    <p class="card-text">
                        <small class="text-{% if product.stock > 10 %}success{% elif product.stock > 0 %}warning{% else %}danger{% endif %}">
                            Stock: {{ product.stock }}
                        </small>
                    </p>
                    <div class="d-flex gap-2">
                        <a href="{{ url_for('product_detail', product_id=product.id) }}" class="btn btn-outline-primary flex-grow-1">
                            <i class="fas fa-eye"></i> Voir
                        </a>
                        <button class="btn btn-primary add-to-cart" data-product-id="{{ product.id }}">
                            <i class="fas fa-cart-plus"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    {% endfor %}
</div>

<script>
$(document).ready(function() {
    $('.add-to-cart').click(function() {
        const productId = $(this).data('product-id');
        
        $.post('/add_to_cart', {
            product_id: productId,
            quantity: 1
        }, function(response) {
            if (response.success) {
                alert('Produit ajouté au panier !');
                updateCartCount();
            } else {
                alert(response.message);
            }
        });
    });
});
</script>
{% endblock %}
```

### product.html
```html
{% extends "base.html" %}

{% block title %}{{ product.name }} - Ma Boutique{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-6">
        {% if product.image_url %}
        <img src="{{ product.image_url }}" class="img-fluid rounded" alt="{{ product.name }}">
        {% else %}
        <div class="bg-secondary rounded d-flex align-items-center justify-content-center" style="height: 400px;">
            <i class="fas fa-image fa-5x text-white"></i>
        </div>
        {% endif %}
    </div>
    <div class="col-md-6">
        <h1>{{ product.name }}</h1>
        <p class="text-muted">Référence: #{{ product.id }}</p>
        
        <div class="mb-3">
            <span class="h2 text-primary">{{ product.price }} €</span>
        </div>
        
        <div class="mb-3">
            <span class="badge bg-{% if product.stock > 10 %}success{% elif product.stock > 0 %}warning{% else %}danger{% endif %}">
                {% if product.stock > 0 %}
                {{ product.stock }} en stock
                {% else %}
                Rupture de stock
                {% endif %}
            </span>
        </div>
        
        <p class="mb-4">{{ product.description }}</p>
        
        {% if product.stock > 0 %}
        <form id="add-to-cart-form" class="mb-3">
            <div class="row g-3 align-items-center">
                <div class="col-auto">
                    <label for="quantity" class="col-form-label">Quantité:</label>
                </div>
                <div class="col-auto">
                    <input type="number" id="quantity" name="quantity" class="form-control" value="1" min="1" max="{{ product.stock }}">
                </div>
                <div class="col-auto">
                    <button type="button" class="btn btn-primary btn-lg" id="add-to-cart-btn">
                        <i class="fas fa-cart-plus"></i> Ajouter au panier
                    </button>
                </div>
            </div>
        </form>
        {% else %}
        <button class="btn btn-secondary btn-lg" disabled>
            <i class="fas fa-times"></i> Produit indisponible
        </button>
        {% endif %}
        
        <div class="mt-4">
            <a href="{{ url_for('index') }}" class="btn btn-outline-secondary">
                <i class="fas fa-arrow-left"></i> Retour aux produits
            </a>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    $('#add-to-cart-btn').click(function() {
        const quantity = $('#quantity').val();
        
        $.post('/add_to_cart', {
            product_id: {{ product.id }},
            quantity: quantity
        }, function(response) {
            if (response.success) {
                alert('Produit ajouté au panier !');
                updateCartCount();
            } else {
                alert(response.message);
            }
        });
    });
});
</script>
{% endblock %}
```

### cart.html
```html
{% extends "base.html" %}

{% block title %}Panier - Ma Boutique{% endblock %}

{% block content %}
<h1 class="mb-4">Votre Panier</h1>

{% if cart_items %}
<div class="table-responsive">
    <table class="table">
        <thead>
            <tr>
                <th>Produit</th>
                <th>Prix unitaire</th>
                <th>Quantité</th>
                <th>Total</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for item in cart_items %}
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        {% if item.image_url %}
                        <img src="{{ item.image_url }}" alt="{{ item.name }}" style="width: 50px; height: 50px; object-fit: cover;" class="me-3">
                        {% endif %}
                        <div>
                            <h6 class="mb-0">{{ item.name }}</h6>
                            <small class="text-muted">Stock: {{ item.stock }}</small>
                        </div>
                    </div>
                </td>
                <td>{{ item.price }} €</td>
                <td>
                    <div class="input-group" style="width: 120px;">
                        <input type="number" class="form-control quantity-input" 
                               value="{{ item.quantity }}" min="1" max="{{ item.stock }}"
                               data-item-id="{{ item.id }}">
                        <button class="btn btn-outline-secondary update-quantity" type="button">
                            <i class="fas fa-sync-alt"></i>
                        </button>
                    </div>
                </td>
                <td>{{ item.price * item.quantity }} €</td>
                <td>
                    <a href="{{ url_for('remove_from_cart', item_id=item.id) }}" class="btn btn-danger btn-sm">
                        <i class="fas fa-trash"></i>
                    </a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<div class="row">
    <div class="col-md-6 offset-md-6">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Récapitulatif</h5>
                <div class="d-flex justify-content-between mb-2">
                    <span>Sous-total:</span>
                    <span>{{ total }} €</span>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span>Livraison:</span>
                    <span>Gratuite</span>
                </div>
                <hr>
                <div class="d-flex justify-content-between">
                    <strong>Total:</strong>
                    <strong>{{ total }} €</strong>
                </div>
                <div class="mt-3">
                    {% if current_user.is_authenticated %}
                    <a href="{{ url_for('checkout') }}" class="btn btn-primary btn-lg w-100">
                        <i class="fas fa-credit-card"></i> Passer la commande
                    </a>
                    {% else %}
                    <div class="alert alert-warning">
                        <p>Vous devez être connecté pour passer commande.</p>
                        <a href="{{ url_for('login') }}" class="btn btn-primary">Se connecter</a>
                        <a href="{{ url_for('register') }}" class="btn btn-outline-primary">S'inscrire</a>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>

<div class="mt-3">
    <a href="{{ url_for('index') }}" class="btn btn-outline-secondary">
        <i class="fas fa-arrow-left"></i> Continuer mes achats
    </a>
</div>

{% else %}
<div class="text-center py-5">
    <i class="fas fa-shopping-cart fa-5x text-muted mb-4"></i>
    <h3>Votre panier est vide</h3>
    <p class="text-muted">Ajoutez des produits pour commencer vos achats</p>
    <a href="{{ url_for('index') }}" class="btn btn-primary">
        <i class="fas fa-store"></i> Voir les produits
    </a>
</div>
{% endif %}

<script>
$(document).ready(function() {
    $('.update-quantity').click(function() {
        const input = $(this).siblings('.quantity-input');
        const itemId = input.data('item-id');
        const quantity = input.val();
        
        $.post('/update_cart', {
            item_id: itemId,
            quantity: quantity
        }, function(response) {
            if (response.success) {
                location.reload();
            } else {
                alert(response.message);
            }
        });
    });
    
    $('.quantity-input').keypress(function(e) {
        if (e.which === 13) {
            $(this).siblings('.update-quantity').click();
        }
    });
});
</script>
{% endblock %}
```

### checkout.html
```html
{% extends "base.html" %}

{% block title %}Paiement - Ma Boutique{% endblock %}

{% block content %}
<h1 class="mb-4">Finaliser la commande</h1>

<div class="row">
    <div class="col-md-8">
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">Adresse de livraison</h5>
            </div>
            <div class="card-body">
                <form id="checkout-form" method="POST" action="{{ url_for('place_order') }}">
                    <div class="mb-3">
                        <label for="shipping_address" class="form-label">Adresse complète *</label>
                        <textarea class="form-control" id="shipping_address" name="shipping_address" 
                                  rows="3" required placeholder="Nom, adresse, code postal, ville..."></textarea>
                    </div>
                    
                    <div class="card mb-4">
                        <div class="card-header">
                            <h5 class="mb-0">Paiement</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-12 mb-3">
                                    <label for="card_number" class="form-label">Numéro de carte *</label>
                                    <input type="text" class="form-control" id="card_number" 
                                           name="card_number" placeholder="1234 5678 9012 3456" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label for="card_expiry" class="form-label">Date d'expiration *</label>
                                    <input type="text" class="form-control" id="card_expiry" 
                                           name="card_expiry" placeholder="MM/AA" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label for="card_cvv" class="form-label">CVV *</label>
                                    <input type="text" class="form-control" id="card_cvv" 
                                           name="card_cvv" placeholder="123" required>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i> 
                        Ceci est une démonstration. Aucun paiement réel ne sera effectué.
                    </div>
                    
                    <button type="submit" class="btn btn-primary btn-lg w-100">
                        <i class="fas fa-lock"></i> Payer {{ total }} €
                    </button>
                </form>
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Récapitulatif</h5>
            </div>
            <div class="card-body">
                <h6>Votre commande ({{ cart_items|length }} articles)</h6>
                <ul class="list-group list-group-flush mb-3">
                    {% for item in cart_items %}
                    <li class="list-group-item d-flex justify-content-between">
                        <span>{{ item.quantity }} × {{ item.name }}</span>
                        <span>{{ item.price * item.quantity }} €</span>
                    </li>
                    {% endfor %}
                </ul>
                
                <div class="d-flex justify-content-between mb-2">
                    <span>Sous-total:</span>
                    <span>{{ total }} €</span>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span>Livraison:</span>
                    <span>Gratuite</span>
                </div>
                <hr>
                <div class="d-flex justify-content-between">
                    <strong>Total:</strong>
                    <strong>{{ total }} €</strong>
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <a href="{{ url_for('cart') }}" class="btn btn-outline-secondary w-100">
                <i class="fas fa-arrow-left"></i> Retour au panier
            </a>
        </div>
    </div>
</div>
{% endblock %}
```

### order_confirmation.html
```html
{% extends "base.html" %}

{% block title %}Confirmation - Ma Boutique{% endblock %}

{% block content %}
<div class="text-center py-5">
    <div class="mb-4">
        <i class="fas fa-check-circle fa-5x text-success"></i>
    </div>
    
    <h1 class="mb-3">Commande confirmée !</h1>
    <p class="lead mb-4">Merci pour votre achat. Votre commande a été enregistrée avec succès.</p>
    
    <div class="card mx-auto mb-4" style="max-width: 500px;">
        <div class="card-body">
            <h5 class="card-title">Détails de la commande</h5>
            <p class="card-text">
                <strong>Numéro de commande:</strong> #{{ order_id }}<br>
                <strong>Montant total:</strong> {{ total }} €<br>
                <strong>Date:</strong> {{ now.strftime('%d/%m/%Y %H:%M') }}
            </p>
        </div>
    </div>
    
    <p class="text-muted mb-4">
        Un email de confirmation vous a été envoyé (simulation).<br>
        Vous pouvez suivre votre commande dans votre espace client.
    </p>
    
    <div class="d-flex justify-content-center gap-3">
        <a href="{{ url_for('account') }}" class="btn btn-primary">
            <i class="fas fa-user"></i> Voir mes commandes
        </a>
        <a href="{{ url_for('index') }}" class="btn btn-outline-primary">
            <i class="fas fa-store"></i> Retour à la boutique
        </a>
    </div>
</div>
{% endblock %}
```

### login.html
```html
{% extends "base.html" %}

{% block title %}Connexion - Ma Boutique{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">Connexion</h4>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('login') }}">
                    <div class="mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email" class="form-control" id="email" name="email" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Mot de passe</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <div class="d-grid gap-2">
                        <button type="submit" class="btn btn-primary">Se connecter</button>
                    </div>
                </form>
                
                <div class="mt-3 text-center">
                    <p>Pas encore de compte ? <a href="{{ url_for('register') }}">S'inscrire</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### register.html
```html
{% extends "base.html" %}

{% block title %}Inscription - Ma Boutique{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">Créer un compte</h4>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('register') }}">
                    <div class="mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email" class="form-control" id="email" name="email" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Mot de passe</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <div class="mb-3">
                        <label for="confirm_password" class="form-label">Confirmer le mot de passe</label>
                        <input type="password" class="form-control" id="confirm_password" name="confirm_password" required>
                    </div>
                    <div class="d-grid gap-2">
                        <button type="submit" class="btn btn-primary">S'inscrire</button>
                    </div>
                </form>
                
                <div class="mt-3 text-center">
                    <p>Déjà un compte ? <a href="{{ url_for('login') }}">Se connecter</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### account.html
```html
{% extends "base.html" %}

{% block title %}Mon compte - Ma Boutique{% endblock %}

{% block content %}
<h1 class="mb-4">Mon compte</h1>

<div class="row">
    <div class="col-md-4">
        <div class="card mb-4">
            <div class="card-body text-center">
                <div class="mb-3">
                    <i class="fas fa-user-circle fa-5x text-primary"></i>
                </div>
                <h5>{{ current_user.email }}</h5>
                <p class="text-muted">Membre depuis {{ current_user.created_at.strftime('%d/%m/%Y') if current_user.created_at else 'récemment' }}</p>
            </div>
        </div>
    </div>
    
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Mes commandes</h5>
            </div>
            <div class="card-body">
                {% if orders %}
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>N° Commande</th>
                                <th>Date</th>
                                <th>Total</th>
                                <th>Statut</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for order in orders %}
                            <tr>
                                <td>#{{ order.id }}</td>
                                <td>{{ order.created_at.strftime('%d/%m/%Y') }}</td>
                                <td>{{ order.total }} €</td>
                                <td>
                                    <span class="badge bg-{% if order.status == 'completed' %}success{% elif order.status == 'processing' %}warning{% elif order.status == 'cancelled' %}danger{% else %}info{% endif %}">
                                        {{ order.status }}
                                    </span>
                                </td>
                                <td>
                                    <a href="#" class="btn btn-sm btn-outline-primary">
                                        <i class="fas fa-eye"></i> Détails
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="text-center py-4">
                    <i class="fas fa-box-open fa-3x text-muted mb-3"></i>
                    <p class="text-muted">Vous n'avez pas encore passé de commande.</p>
                    <a href="{{ url_for('index') }}" class="btn btn-primary">
                        <i class="fas fa-store"></i> Découvrir nos produits
                    </a>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### admin.html
```html
{% extends "base.html" %}

{% block title %}Administration - Ma Boutique{% endblock %}

{% block content %}
<h1 class="mb-4">Tableau de bord Admin</h1>

<div class="row mb-4">
    <div class="col-md-4">
        <div class="card text-white bg-primary">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="card-title">Produits</h6>
                        <h2 class="mb-0">{{ total_products }}</h2>
                    </div>
                    <i class="fas fa-box fa-3x opacity-50"></i>
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card text-white bg-success">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="card-title">Commandes</h6>
                        <h2 class="mb-0">{{ total_orders }}</h2>
                    </div>
                    <i class="fas fa-shopping-cart fa-3x opacity-50"></i>
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card text-white bg-warning">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="card-title">Clients</h6>
                        <h2 class="mb-0">{{ total_users }}</h2>
                    </div>
                    <i class="fas fa-users fa-3x opacity-50"></i>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Dernières commandes</h5>
            </div>
            <div class="card-body">
                {% if recent_orders %}
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>N° Commande</th>
                                <th>Client</th>
                                <th>Total</th>
                                <th>Statut</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for order in recent_orders %}
                            <tr>
                                <td>#{{ order.id }}</td>
                                <td>{{ order.email }}</td>
                                <td>{{ order.total }} €</td>
                                <td>
                                    <span class="badge bg-{% if order.status == 'completed' %}success{% elif order.status == 'processing' %}warning{% elif order.status == 'cancelled' %}danger{% else %}info{% endif %}">
                                        {{ order.status }}
                                    </span>
                                </td>
                                <td>{{ order.created_at.strftime('%d/%m/%Y') }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                <a href="{{ url_for('admin_orders') }}" class="btn btn-outline-primary">Voir toutes les commandes</a>
                {% else %}
                <p class="text-muted">Aucune commande récente.</p>
                {% endif %}
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Actions rapides</h5>
            </div>
            <div class="card-body">
                <div class="d-grid gap-2">
                    <a href="{{ url_for('admin_products') }}" class="btn btn-primary">
                        <i class="fas fa-box"></i> Gérer les produits
                    </a>
                    <a href="{{ url_for('admin_add_product') }}" class="btn btn-success">
                        <i class="fas fa-plus"></i> Ajouter un produit
                    </a>
                    <a href="{{ url_for('admin_orders') }}" class="btn btn-info">
                        <i class="fas fa-shopping-cart"></i> Voir les commandes
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### admin_products.html
```html
{% extends "base.html" %}

{% block title %}Gestion des produits - Admin{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>Gestion des produits</h1>
    <a href="{{ url_for('admin_add_product') }}" class="btn btn-success">
        <i class="fas fa-plus"></i> Ajouter un produit
    </a>
</div>

<div class="table-responsive">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>ID</th>
                <th>Image</th>
                <th>Nom</th>
                <th>Prix</th>
                <th>Stock</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for product in products %}
            <tr>
                <td>{{ product.id }}</td>
                <td>
                    {% if product.image_url %}
                    <img src="{{ product.image_url }}" alt="{{ product.name }}" style="width: 50px; height: 50px; object-fit: cover;">
                    {% else %}
                    <i class="fas fa-image text-muted"></i>
                    {% endif %}
                </td>
                <td>{{ product.name }}</td>
                <td>{{ product.price }} €</td>
                <td>
                    <span class="badge bg-{% if product.stock > 10 %}success{% elif product.stock > 0 %}warning{% else %}danger{% endif %}">
                        {{ product.stock }}
                    </span>
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <a href="{{ url_for('admin_edit_product', product_id=product.id) }}" class="btn btn-sm btn-outline-primary">
                            <i class="fas fa-edit"></i>
                        </a>
                        <a href="{{ url_for('admin_delete_product', product_id=product.id) }}" 
                           class="btn btn-sm btn-outline-danger"
                           onclick="return confirm('Êtes-vous sûr de vouloir supprimer ce produit ?')">
                            <i class="fas fa-trash"></i>
                        </a>
                    </div>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<div class="mt-3">
    <a href="{{ url_for('admin') }}" class="btn btn-outline-secondary">
        <i class="fas fa-arrow-left"></i> Retour au tableau de bord
    </a>
</div>
{% endblock %}
```

### admin_add_product.html
```html
{% extends "base.html" %}

{% block title %}Ajouter un produit - Admin{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">Ajouter un nouveau produit</h4>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('admin_add_product') }}" enctype="multipart/form-data">
                    <div class="mb-3">
                        <label for="name" class="form-label">Nom du produit *</label>
                        <input type="text" class="form-control" id="name" name="name" required>
                    </div>
                    
                    <div class="mb-3">
                        <label for="description" class="form-label">Description</label>
                        <textarea class="form-control" id="description" name="description" rows="3"></textarea>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="price" class="form-label">Prix (€) *</label>
                            <input type="number" step="0.01" class="form-control" id="price" name="price" required>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="stock" class="form-label">Stock *</label>
                            <input type="number" class="form-control" id="stock" name="stock" required>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="image" class="form-label">Image du produit</label>
                        <input type="file" class="form-control" id="image" name="image" accept="image/*">
                        <small class="text-muted">Formats acceptés: JPG, PNG, GIF. Taille max: 2MB</small>
                    </div>
                    
                    <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                        <a href="{{ url_for('admin_products') }}" class="btn btn-secondary me-md-2">
                            Annuler
                        </a>
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i> Ajouter le produit
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### admin_orders.html
```html
{% extends "base.html" %}

{% block title %}Commandes - Admin{% endblock %}

{% block content %}
<h1 class="mb-4">Gestion des commandes</h1>

<div class="table-responsive">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>N° Commande</th>
                <th>Client</th>
                <th>Total</th>
                <th>Statut</th>
                <th>Date</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for order in orders %}
            <tr>
                <td>#{{ order.id }}</td>
                <td>
                    {% set user = User.get(order.user_id) %}
                    {{ user.email if user else 'Utilisateur supprimé' }}
                </td>
                <td>{{ order.total }} €</td>
                <td>
                    <span class="badge bg-{% if order.status == 'completed' %}success{% elif order.status == 'processing' %}warning{% elif order.status == 'cancelled' %}danger{% else %}info{% endif %}">
                        {{ order.status }}
                    </span>
                </td>
                <td>{{ order.created_at.strftime('%d/%m/%Y %H:%M') }}</td>
                <td>
                    <div class="btn-group" role="group">
                        <a href="{{ url_for('admin_order_detail', order_id=order.id) }}" class="btn btn-sm btn-outline-primary">
                            <i class="fas fa-eye"></i> Détails
                        </a>
                        <div class="btn-group" role="group">
                            <button type="button" class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown">
                                Statut
                            </button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item" href="#" onclick="updateStatus({{ order.id }}, 'pending')">En attente</a></li>
                                <li><a class="dropdown-item" href="#" onclick="updateStatus({{ order.id }}, 'processing')">En traitement</a></li>
                                <li><a class="dropdown-item" href="#" onclick="updateStatus({{ order.id }}, 'completed')">Terminée</a></li>
                                <li><a class="dropdown-item" href="#" onclick="updateStatus({{ order.id }}, 'cancelled')">Annulée</a></li>
                            </ul>
                        </div>
                    </div>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<div class="mt-3">
    <a href="{{ url_for('admin') }}" class="btn btn-outline-secondary">
        <i class="fas fa-arrow-left"></i> Retour au tableau de bord
    </a>
</div>

<script>
function updateStatus(orderId, status) {
    $.post('/admin/update_order_status/' + orderId, {
        status: status
    }, function(response) {
        if (response.success) {
            location.reload();
        } else {
            alert(response.message);
        }
    });
}
</script>
{% endblock %}
```

### admin_order_detail.html
```html
{% extends "base.html" %}

{% block title %}Commande #{{ order.id }} - Admin{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>Commande #{{ order.id }}</h1>
    <a href="{{ url_for('admin_orders') }}" class="btn btn-outline-secondary">
        <i class="fas fa-arrow-left"></i> Retour aux commandes
    </a>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">Articles commandés</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Produit</th>
                                <th>Prix unitaire</th>
                                <th>Quantité</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in order_items %}
                            <tr>
                                <td>{{ item.name }}</td>
                                <td>{{ item.price }} €</td>
                                <td>{{ item.quantity }}</td>
                                <td>{{ item.price * item.quantity }} €</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">Informations client</h5>
            </div>
            <div class="card-body">
                <p><strong>Email:</strong> {{ order.email }}</p>
                <p><strong>ID Client:</strong> {{ order.user_id }}</p>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Récapitulatif</h5>
            </div>
            <div class="card-body">
                <div class="mb-2">
                    <strong>Statut:</strong>
                    <span class="badge bg-{% if order.status == 'completed' %}success{% elif order.status == 'processing' %}warning{% elif order.status == 'cancelled' %}danger{% else %}info{% endif %} ms-2">
                        {{ order.status }}
                    </span>
                </div>
                
                <div class="mb-2">
                    <strong>Date:</strong> {{ order.created_at.strftime('%d/%m/%Y %H:%M') }}
                </div>
                
                <div class="mb-2">
                    <strong>Adresse de livraison:</strong>
                    <p class="mt-1">{{ order.shipping_address }}</p>
                </div>
                
                <hr>
                
                <div class="d-flex justify-content-between">
                    <strong>Total:</strong>
                    <strong>{{ order.total }} €</strong>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### admin_edit_product.html
```html
{% extends "base.html" %}

{% block title %}Modifier le produit - Admin{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">Modifier le produit</h4>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('admin_edit_product', product_id=product.id) }}" enctype="multipart/form-data">
                    <div class="mb-3">
                        <label for="name" class="form-label">Nom du produit *</label>
                        <input type="text" class="form-control" id="name" name="name" value="{{ product.name }}" required>
                    </div>
                    
                    <div class="mb-3">
                        <label for="description" class="form-label">Description</label>
                        <textarea class="form-control" id="description" name="description" rows="3">{{ product.description }}</textarea>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="price" class="form-label">Prix (€) *</label>
                            <input type="number" step="0.01" class="form-control" id="price" name="price" value="{{ product.price }}" required>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="stock" class="form-label">Stock *</label>
                            <input type="number" class="form-control" id="stock" name="stock" value="{{ product.stock }}" required>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="image" class="form-label">Image du produit</label>
                        {% if product.image_url %}
                        <div class="mb-2">
                            <img src="{{ product.image_url }}" alt="{{ product.name }}" style="width: 100px; height: 100px; object-fit: cover;" class="rounded">
                        </div>
                        {% endif %}
                        <input type="file" class="form-control" id="image" name="image" accept="image/*">
                        <small class="text-muted">Laisser vide pour conserver l'image actuelle</small>
                    </div>
                    
                    <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                        <a href="{{ url_for('admin_products') }}"