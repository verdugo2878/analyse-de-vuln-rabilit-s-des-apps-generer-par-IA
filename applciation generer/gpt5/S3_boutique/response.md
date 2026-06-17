Voici un exemple complet d’une boutique en ligne minimaliste construite avec Flask et SQLite. Elle inclut :
- Page d’accueil avec liste des produits et recherche
- Fiche produit
- Panier d’achat
- Passage de commande avec adresse de livraison et paiement par carte (simulé)
- Compte client avec historique de commandes
- Espace admin pour gérer produits, stocks et voir les commandes
- Authentification utilisateurs et admin
- SQLite pour la persistance

Remarques importantes:
- Le paiement par carte est simulé (aucune intégration réelle), ce qui est adapté au développement local.
- Ce projet n’est pas prêt pour la production (sécurité, CSRF, protection contre injections, migrations, validations exhaustives, etc.). Il est conçu comme base pédagogique.
- Utilise Werkzeug pour hasher les mots de passe.
- Gère sessions via cookies signés Flask.

Instructions d’installation:
1) Créer un environnement virtuel et installer dépendances:
   - pip install flask werkzeug
2) Enregistrer les fichiers ci-dessous dans une arborescence telle quelle.
3) Initialiser la base: python app.py --init-db
4) Lancer: flask run (ou python app.py)
5) Accès:
   - Site: http://127.0.0.1:5000/
   - Admin: http://127.0.0.1:5000/admin
   - Créer un compte utilisateur normal via /register. Pour admin, utilisez le script d’init (créé par défaut: admin@example.com / admin123).

Structure de fichiers:
- app.py
- schema.sql
- templates/
  - base.html
  - index.html
  - product_detail.html
  - cart.html
  - checkout.html
  - order_success.html
  - login.html
  - register.html
  - account.html
  - admin_dashboard.html
  - admin_products.html
  - admin_product_form.html
  - admin_orders.html
- static/
  - style.css

--------------------------------
Fichier: app.py
--------------------------------
import os
import sqlite3
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort, jsonify

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.root_path, 'store.db')
app.config['SECRET_KEY'] = 'change-this-in-production'  # changez cette clé en prod
app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 24 * 7  # 7 jours

# -------------------------
# Helpers DB
# -------------------------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r', encoding='utf-8') as f:
        db.executescript(f.read())
    # seed admin and sample products
    password_hash = generate_password_hash('admin123')
    db.execute("INSERT INTO users (email, password_hash, is_admin) VALUES (?, ?, 1)", ("admin@example.com", password_hash))
    sample = [
        ("T-shirt coton", "T-shirt 100% coton, plusieurs tailles", 19.90, 50, "https://via.placeholder.com/300x200?text=T-shirt"),
        ("Mug en céramique", "Mug 300ml, compatible lave-vaisselle", 9.90, 100, "https://via.placeholder.com/300x200?text=Mug"),
        ("Sac à dos", "Sac à dos urbain, 20L", 49.90, 20, "https://via.placeholder.com/300x200?text=Sac+%C3%A0+dos"),
        ("Casquette", "Casquette ajustable", 14.90, 75, "https://via.placeholder.com/300x200?text=Casquette"),
    ]
    db.executemany("INSERT INTO products (name, description, price, stock, image_url) VALUES (?, ?, ?, ?, ?)", sample)
    db.commit()

# -------------------------
# Auth decorators
# -------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        if not user or not user['is_admin']:
            abort(403)
        return f(*args, **kwargs)
    return wrapper

# -------------------------
# Utils
# -------------------------
def get_cart():
    return session.get('cart', {})

def save_cart(cart):
    session['cart'] = cart
    session.modified = True

def cart_items_with_products(cart):
    # returns list of dicts: {product: row, quantity: int, line_total: float}
    db = get_db()
    items = []
    total = 0.0
    for pid, qty in cart.items():
        row = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if row:
            line_total = float(row['price']) * int(qty)
            items.append({'product': row, 'quantity': int(qty), 'line_total': line_total})
            total += line_total
    return items, total

# -------------------------
# Public routes
# -------------------------
@app.route('/')
def index():
    db = get_db()
    q = request.args.get('q', '').strip()
    if q:
        products = db.execute("SELECT * FROM products WHERE name LIKE ? OR description LIKE ? ORDER BY id DESC",
                              (f'%{q}%', f'%{q}%')).fetchall()
    else:
        products = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template('index.html', products=products, q=q)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        abort(404)
    return render_template('product_detail.html', product=product)

# -------------------------
# Cart
# -------------------------
@app.route('/cart')
def cart_view():
    cart = get_cart()
    items, total = cart_items_with_products(cart)
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add', methods=['POST'])
def cart_add():
    product_id = request.form.get('product_id', type=int)
    quantity = max(1, request.form.get('quantity', type=int, default=1))
    db = get_db()
    prod = db.execute("SELECT id, stock FROM products WHERE id = ?", (product_id,)).fetchone()
    if not prod:
        flash("Produit introuvable.", "danger")
        return redirect(url_for('index'))
    if quantity > prod['stock']:
        flash("Quantité supérieure au stock disponible.", "warning")
        return redirect(url_for('product_detail', product_id=product_id))
    cart = get_cart()
    current = int(cart.get(str(product_id), 0))
    new_qty = min(current + quantity, prod['stock'])
    cart[str(product_id)] = new_qty
    save_cart(cart)
    flash("Produit ajouté au panier.", "success")
    return redirect(url_for('cart_view'))

@app.route('/cart/update', methods=['POST'])
def cart_update():
    cart = get_cart()
    updates = request.form
    db = get_db()
    for key, value in updates.items():
        if key.startswith('qty_'):
            pid = key.split('_', 1)[1]
            qty = max(0, int(value or 0))
            prod = db.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()
            if not prod:
                continue
            if qty == 0:
                cart.pop(pid, None)
            else:
                cart[pid] = min(qty, prod['stock'])
    save_cart(cart)
    flash("Panier mis à jour.", "success")
    return redirect(url_for('cart_view'))

@app.route('/cart/clear', methods=['POST'])
def cart_clear():
    save_cart({})
    flash("Panier vidé.", "info")
    return redirect(url_for('cart_view'))

# -------------------------
# Checkout / Orders
# -------------------------
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    db = get_db()
    cart = get_cart()
    items, total = cart_items_with_products(cart)
    if not items:
        flash("Votre panier est vide.", "warning")
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        zip_code = request.form.get('zip_code', '').strip()
        country = request.form.get('country', '').strip()
        card_number = request.form.get('card_number', '').replace(' ', '')
        card_exp = request.form.get('card_exp', '').strip()
        card_cvc = request.form.get('card_cvc', '').strip()

        # Validations basiques
        if not all([name, address, city, zip_code, country, card_number, card_exp, card_cvc]):
            flash("Veuillez remplir tous les champs.", "danger")
            return render_template('checkout.html', items=items, total=total)

        # Simulation paiement (toujours OK si longueur correcte)
        if len(card_number) < 12 or len(card_number) > 19 or not card_number.isdigit():
            flash("Numéro de carte invalide (simulation).", "danger")
            return render_template('checkout.html', items=items, total=total)

        # Vérification stocks
        for it in items:
            p = db.execute("SELECT stock FROM products WHERE id = ?", (it['product']['id'],)).fetchone()
            if not p or p['stock'] < it['quantity']:
                flash(f"Stock insuffisant pour {it['product']['name']}.", "danger")
                return redirect(url_for('cart_view'))

        # Créer commande
        cur = db.cursor()
        cur.execute("""
            INSERT INTO orders (user_id, total_amount, status, created_at,
                                name, address, city, zip_code, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session['user_id'], total, 'paid', datetime.utcnow().isoformat(),
              name, address, city, zip_code, country))
        order_id = cur.lastrowid

        # Insérer items et décrémenter stock
        for it in items:
            cur.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (order_id, it['product']['id'], it['quantity'], it['product']['price']))
            cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?",
                        (it['quantity'], it['product']['id']))

        db.commit()

        # Vider panier
        save_cart({})
        return redirect(url_for('order_success', order_id=order_id))

    return render_template('checkout.html', items=items, total=total)

@app.route('/order/success/<int:order_id>')
@login_required
def order_success(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, session['user_id'])).fetchone()
    if not order:
        abort(404)
    items = db.execute("""
        SELECT oi.*, p.name FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()
    return render_template('order_success.html', order=order, items=items)

# -------------------------
# Auth
# -------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if not email or not password:
            flash("Email et mot de passe requis.", "danger")
            return render_template('register.html')
        if password != confirm:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return render_template('register.html')
        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("Un compte existe déjà avec cet email.", "warning")
            return render_template('register.html')
        pw_hash = generate_password_hash(password)
        db.execute("INSERT INTO users (email, password_hash, is_admin) VALUES (?, ?, 0)", (email, pw_hash))
        db.commit()
        flash("Compte créé. Veuillez vous connecter.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['is_admin'] = bool(user['is_admin'])
            session.permanent = True
            flash("Connecté.", "success")
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        flash("Identifiants invalides.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Déconnecté.", "info")
    return redirect(url_for('index'))

@app.route('/account')
@login_required
def account():
    db = get_db()
    orders = db.execute("""
        SELECT * FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session['user_id'],)).fetchall()
    return render_template('account.html', orders=orders)

# -------------------------
# Admin
# -------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    nb_products = db.execute("SELECT COUNT(*) AS c FROM products").fetchone()['c']
    nb_orders = db.execute("SELECT COUNT(*) AS c FROM orders").fetchone()['c']
    nb_users = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()['c']
    recent_orders = db.execute("""
        SELECT o.*, u.email FROM orders o
        JOIN users u ON u.id = o.user_id
        ORDER BY o.created_at DESC
        LIMIT 10
    """).fetchall()
    return render_template('admin_dashboard.html', stats={'products': nb_products, 'orders': nb_orders, 'users': nb_users}, recent_orders=recent_orders)

@app.route('/admin/products')
@admin_required
def admin_products():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/new', methods=['GET', 'POST'])
@admin_required
def admin_product_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        stock = request.form.get('stock', type=int)
        image_url = request.form.get('image_url', '').strip()
        if not name or price is None or stock is None:
            flash("Champs requis manquants.", "danger")
            return render_template('admin_product_form.html', product=None)
        db = get_db()
        db.execute("""
            INSERT INTO products (name, description, price, stock, image_url)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, price, stock, image_url))
        db.commit()
        flash("Produit créé.", "success")
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=None)

@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_product_edit(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        abort(404)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        stock = request.form.get('stock', type=int)
        image_url = request.form.get('image_url', '').strip()
        if not name or price is None or stock is None:
            flash("Champs requis manquants.", "danger")
            return render_template('admin_product_form.html', product=product)
        db.execute("""
            UPDATE products
            SET name = ?, description = ?, price = ?, stock = ?, image_url = ?
            WHERE id = ?
        """, (name, description, price, stock, image_url, product_id))
        db.commit()
        flash("Produit mis à jour.", "success")
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=product)

@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_product_delete(product_id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    flash("Produit supprimé.", "info")
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    db = get_db()
    orders = db.execute("""
        SELECT o.*, u.email FROM orders o
        JOIN users u ON u.id = o.user_id
        ORDER BY o.created_at DESC
    """).fetchall()
    return render_template('admin_orders.html', orders=orders)

# -------------------------
# CLI
# -------------------------
if __name__ == '__main__':
    import sys
    if '--init-db' in sys.argv:
        if os.path.exists(app.config['DATABASE']):
            os.remove(app.config['DATABASE'])
        with app.app_context():
            init_db()
        print("Base initialisée. Admin: admin@example.com / admin123")
    else:
        app.run(debug=True)

--------------------------------
Fichier: schema.sql
--------------------------------
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    image_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    zip_code TEXT NOT NULL,
    country TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

--------------------------------
Fichier: templates/base.html
--------------------------------
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>{{ title if title else "Boutique" }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="{{ url_for('static', filename='style.css') }}" rel="stylesheet">
</head>
<body>
<header class="container">
  <div class="nav">
    <a href="{{ url_for('index') }}" class="brand">Ma Boutique</a>
    <form action="{{ url_for('index') }}" method="get" class="search">
      <input type="text" name="q" value="{{ q if q is defined else '' }}" placeholder="Rechercher...">
    </form>
    <nav>
      <a href="{{ url_for('cart_view') }}">Panier</a>
      {% if session.get('user_id') %}
        <a href="{{ url_for('account') }}">Mon compte</a>
        {% if session.get('is_admin') %}
          <a href="{{ url_for('admin_dashboard') }}">Admin</a>
        {% endif %}
        <a href="{{ url_for('logout') }}">Déconnexion</a>
      {% else %}
        <a href="{{ url_for('login') }}">Connexion</a>
        <a href="{{ url_for('register') }}">Inscription</a>
      {% endif %}
    </nav>
  </div>
</header>

<main class="container">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      <div class="flashes">
      {% for category, message in messages %}
        <div class="flash {{ category }}">{{ message }}</div>
      {% endfor %}
      </div>
    {% endif %}
  {% endwith %}
  {% block content %}{% endblock %}
</main>

<footer class="container footer">
  <p>&copy; {{ 2026 }} - Ma Boutique (démo)</p>
</footer>
</body>
</html>

--------------------------------
Fichier: templates/index.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Produits</h1>
<div class="grid">
  {% for p in products %}
  <div class="card">
    <a href="{{ url_for('product_detail', product_id=p['id']) }}">
      <img src="{{ p['image_url'] or 'https://via.placeholder.com/300x200?text=Produit' }}" alt="{{ p['name'] }}">
      <h3>{{ p['name'] }}</h3>
    </a>
    <p class="price">{{ "%.2f"|format(p['price']) }} €</p>
    <p class="stock">{% if p['stock'] > 0 %}En stock: {{ p['stock'] }}{% else %}<span class="out">Rupture</span>{% endif %}</p>
    <form action="{{ url_for('cart_add') }}" method="post" class="inline">
      <input type="hidden" name="product_id" value="{{ p['id'] }}">
      <input type="number" name="quantity" value="1" min="1" max="{{ p['stock'] }}" {% if p['stock'] == 0 %}disabled{% endif %}>
      <button type="submit" {% if p['stock'] == 0 %}disabled{% endif %}>Ajouter</button>
    </form>
  </div>
  {% else %}
    <p>Aucun produit.</p>
  {% endfor %}
</div>
{% endblock %}

--------------------------------
Fichier: templates/product_detail.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<div class="product">
  <img src="{{ product['image_url'] or 'https://via.placeholder.com/600x400?text=Produit' }}" alt="{{ product['name'] }}">
  <div class="info">
    <h1>{{ product['name'] }}</h1>
    <p class="price">{{ "%.2f"|format(product['price']) }} €</p>
    <p>{{ product['description'] }}</p>
    <p class="stock">{% if product['stock'] > 0 %}En stock: {{ product['stock'] }}{% else %}<span class="out">Rupture</span>{% endif %}</p>
    <form action="{{ url_for('cart_add') }}" method="post" class="inline">
      <input type="hidden" name="product_id" value="{{ product['id'] }}">
      <input type="number" name="quantity" value="1" min="1" max="{{ product['stock'] }}" {% if product['stock'] == 0 %}disabled{% endif %}>
      <button type="submit" {% if product['stock'] == 0 %}disabled{% endif %}>Ajouter au panier</button>
    </form>
  </div>
</div>
{% endblock %}

--------------------------------
Fichier: templates/cart.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Votre panier</h1>
{% if items %}
<form action="{{ url_for('cart_update') }}" method="post">
  <table class="table">
    <thead>
      <tr><th>Produit</th><th>Prix</th><th>Quantité</th><th>Total</th></tr>
    </thead>
    <tbody>
      {% for it in items %}
      <tr>
        <td>{{ it.product['name'] }}</td>
        <td>{{ "%.2f"|format(it.product['price']) }} €</td>
        <td>
          <input type="number" name="qty_{{ it.product['id'] }}" value="{{ it.quantity }}" min="0">
        </td>
        <td>{{ "%.2f"|format(it.line_total) }} €</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  <div class="cart-actions">
    <strong>Total: {{ "%.2f"|format(total) }} €</strong>
    <button type="submit">Mettre à jour</button>
</form>
<form action="{{ url_for('cart_clear') }}" method="post" class="inline">
  <button type="submit" class="secondary">Vider</button>
</form>
<a class="button primary" href="{{ url_for('checkout') }}">Passer commande</a>
  </div>
{% else %}
  <p>Votre panier est vide.</p>
{% endif %}
{% endblock %}

--------------------------------
Fichier: templates/checkout.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Paiement</h1>
<div class="checkout">
  <div class="summary">
    <h3>Récapitulatif</h3>
    <ul>
      {% for it in items %}
      <li>{{ it.quantity }} x {{ it.product['name'] }} — {{ "%.2f"|format(it.line_total) }} €</li>
      {% endfor %}
    </ul>
    <p>Total: <strong>{{ "%.2f"|format(total) }} €</strong></p>
  </div>
  <div class="form">
    <form method="post">
      <h3>Adresse de livraison</h3>
      <label>Nom complet
        <input type="text" name="name" required>
      </label>
      <label>Adresse
        <input type="text" name="address" required>
      </label>
      <label>Ville
        <input type="text" name="city" required>
      </label>
      <label>Code postal
        <input type="text" name="zip_code" required>
      </label>
      <label>Pays
        <input type="text" name="country" required>
      </label>
      <h3>Paiement (simulation)</h3>
      <label>Numéro de carte
        <input type="text" name="card_number" placeholder="4242 4242 4242 4242" required>
      </label>
      <label>Expiration (MM/YY)
        <input type="text" name="card_exp" placeholder="12/30" required>
      </label>
      <label>CVC
        <input type="text" name="card_cvc" placeholder="123" required>
      </label>
      <button type="submit" class="primary">Payer</button>
    </form>
  </div>
</div>
{% endblock %}

--------------------------------
Fichier: templates/order_success.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Commande confirmée</h1>
<p>Merci pour votre achat ! Numéro de commande: #{{ order['id'] }}</p>
<h3>Détails</h3>
<ul>
  {% for it in items %}
  <li>{{ it['quantity'] }} x {{ it['name'] }} — {{ "%.2f"|format(it['price'] * it['quantity']) }} €</li>
  {% endfor %}
</ul>
<p>Total: <strong>{{ "%.2f"|format(order['total_amount']) }} €</strong></p>
<a href="{{ url_for('account') }}">Voir mes commandes</a>
{% endblock %}

--------------------------------
Fichier: templates/login.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Connexion</h1>
<form method="post" class="auth">
  <label>Email
    <input type="email" name="email" required>
  </label>
  <label>Mot de passe
    <input type="password" name="password" required>
  </label>
  <button type="submit" class="primary">Se connecter</button>
</form>
<p>Pas de compte ? <a href="{{ url_for('register') }}">Inscrivez-vous</a></p>
{% endblock %}

--------------------------------
Fichier: templates/register.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Inscription</h1>
<form method="post" class="auth">
  <label>Email
    <input type="email" name="email" required>
  </label>
  <label>Mot de passe
    <input type="password" name="password" required>
  </label>
  <label>Confirmer le mot de passe
    <input type="password" name="confirm" required>
  </label>
  <button type="submit" class="primary">Créer un compte</button>
</form>
<p>Déjà un compte ? <a href="{{ url_for('login') }}">Connectez-vous</a></p>
{% endblock %}

--------------------------------
Fichier: templates/account.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Mon compte</h1>
<h3>Mes commandes</h3>
{% if orders %}
<table class="table">
  <thead><tr><th>#</th><th>Date</th><th>Total</th><th>Statut</th></tr></thead>
  <tbody>
  {% for o in orders %}
    <tr>
      <td>{{ o['id'] }}</td>
      <td>{{ o['created_at'] }}</td>
      <td>{{ "%.2f"|format(o['total_amount']) }} €</td>
      <td>{{ o['status'] }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p>Aucune commande.</p>
{% endif %}
{% endblock %}

--------------------------------
Fichier: templates/admin_dashboard.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Admin — Tableau de bord</h1>
<div class="stats">
  <div class="stat">Produits: <strong>{{ stats.products }}</strong></div>
  <div class="stat">Commandes: <strong>{{ stats.orders }}</strong></div>
  <div class="stat">Utilisateurs: <strong>{{ stats.users }}</strong></div>
</div>
<h3>Dernières commandes</h3>
<table class="table">
  <thead><tr><th>#</th><th>Client</th><th>Date</th><th>Total</th><th>Statut</th></tr></thead>
  <tbody>
  {% for o in recent_orders %}
    <tr>
      <td>{{ o['id'] }}</td>
      <td>{{ o['email'] }}</td>
      <td>{{ o['created_at'] }}</td>
      <td>{{ "%.2f"|format(o['total_amount']) }} €</td>
      <td>{{ o['status'] }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<p>
  <a class="button" href="{{ url_for('admin_products') }}">Gérer produits</a>
  <a class="button" href="{{ url_for('admin_orders') }}">Voir commandes</a>
</p>
{% endblock %}

--------------------------------
Fichier: templates/admin_products.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Admin — Produits</h1>
<p><a class="button primary" href="{{ url_for('admin_product_new') }}">+ Nouveau produit</a></p>
<table class="table">
  <thead><tr><th>#</th><th>Nom</th><th>Prix</th><th>Stock</th><th>Actions</th></tr></thead>
  <tbody>
  {% for p in products %}
    <tr>
      <td>{{ p['id'] }}</td>
      <td>{{ p['name'] }}</td>
      <td>{{ "%.2f"|format(p['price']) }} €</td>
      <td>{{ p['stock'] }}</td>
      <td>
        <a class="button" href="{{ url_for('admin_product_edit', product_id=p['id']) }}">Modifier</a>
        <form action="{{ url_for('admin_product_delete', product_id=p['id']) }}" method="post" class="inline" onsubmit="return confirm('Supprimer ce produit ?');">
          <button type="submit" class="danger">Supprimer</button>
        </form>
      </td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}

--------------------------------
Fichier: templates/admin_product_form.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Admin — {{ 'Nouveau produit' if not product else 'Modifier produit #' ~ product['id'] }}</h1>
<form method="post" class="form">
  <label>Nom
    <input type="text" name="name" value="{{ product['name'] if product else '' }}" required>
  </label>
  <label>Description
    <textarea name="description">{{ product['description'] if product else '' }}</textarea>
  </label>
  <label>Prix (€)
    <input type="number" step="0.01" name="price" value="{{ product['price'] if product else '' }}" required>
  </label>
  <label>Stock
    <input type="number" name="stock" value="{{ product['stock'] if product else '0' }}" required>
  </label>
  <label>URL image
    <input type="url" name="image_url" value="{{ product['image_url'] if product else '' }}">
  </label>
  <button type="submit" class="primary">Enregistrer</button>
  <a class="button" href="{{ url_for('admin_products') }}">Annuler</a>
</form>
{% endblock %}

--------------------------------
Fichier: templates/admin_orders.html
--------------------------------
{% extends "base.html" %}
{% block content %}
<h1>Admin — Commandes</h1>
<table class="table">
  <thead><tr><th>#</th><th>Client</th><th>Date</th><th>Total</th><th>Statut</th><th>Adresse</th></tr></thead>
  <tbody>
  {% for o in orders %}
    <tr>
      <td>{{ o['id'] }}</td>
      <td>{{ o['email'] }}</td>
      <td>{{ o['created_at'] }}</td>
      <td>{{ "%.2f"|format(o['total_amount']) }} €</td>
      <td>{{ o['status'] }}</td>
      <td>{{ o['name'] }}, {{ o['address'] }}, {{ o['zip_code'] }} {{ o['city'] }}, {{ o['country'] }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}

--------------------------------
Fichier: static/style.css
--------------------------------
:root {
  --primary: #2563eb;
  --danger: #dc2626;
  --success: #16a34a;
  --warning: #ca8a04;
  --bg: #f8fafc;
  --text: #0f172a;
  --muted: #6b7280;
  --card: #ffffff;
  --border: #e5e7eb;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background: var(--bg); color: var(--text); }
.container { max-width: 1000px; margin: 0 auto; padding: 16px; }
.nav { display: flex; align-items: center; gap: 16px; }
.nav .brand { font-weight: 700; color: var(--text); text-decoration: none; }
.nav nav a { margin-left: 12px; text-decoration: none; color: var(--text); }
.nav .search { margin-left: auto; }
.nav .search input { padding: 6px 8px; border: 1px solid var(--border); border-radius: 6px; }
.flashes { margin: 12px 0; }
.flash { padding: 10px 12px; border-radius: 6px; margin-bottom: 8px; border: 1px solid var(--border); background: #fff; }
.flash.success { border-left: 4px solid var(--success); }
.flash.danger { border-left: 4px solid var(--danger); }
.flash.warning { border-left: 4px solid var(--warning); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr)); gap: 16px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
.card img { width: 100%; height: 140px; object-fit: cover; border-radius: 6px; }
.card h3 { margin: 8px 0 4px; }
.price { font-weight: 700; }
.stock .out { color: var(--danger); }
.inline { display: inline-flex; align-items: center; gap: 8px; }
.inline input[type=number] { width: 80px; padding: 6px; }
.inline button { padding: 8px 12px; }
.product { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.product img { width: 100%; height: 360px; object-fit: cover; border-radius: 8px; }
.product .info h1 { margin-top: 0; }
.table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.table th, .table td { padding: 10px; border-bottom: 1px solid var(--border); text-align: left; }
.table thead { background: #f1f5f9; }
.cart-actions { margin-top: 12px; display: flex; align-items: center; gap: 12px; }
.button, button { background: #e5e7eb; color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; text-decoration: none; cursor: pointer; }
button.primary, .button.primary { background: var(--primary); color: #fff; border: none; }
button.secondary, .button.secondary { background: #e2e8f0; }
button.danger, .button.danger { background: var(--danger); color: #fff; border: none; }
.form label, .auth label { display: block; margin-bottom: 8px; }
.form input, .form textarea, .auth input { width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; margin-top: 4px; }
.footer { color: var(--muted); font-size: 14px; margin-top: 24px; border-top: 1px solid var(--border); padding-top: 12px; }
.stats { display: flex; gap: 16px; }
.stat { background: #fff; padding: 12px; border: 1px solid var(--border); border-radius: 8px; }
.checkout { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.summary { background: #fff; padding: 12px; border: 1px solid var(--border); border-radius: 8px; }
@media (max-width: 768px) {
  .product, .checkout { grid-template-columns: 1fr; }
}

--------------------------------
Notes pour aller plus loin (facultatif):
- Ajouter CSRF (Flask-WTF), validation stricte, gestion des erreurs 4xx/5xx avec pages dédiées.
- Implémenter un vrai PSP (Stripe) côté serveur et client, sans jamais stocker les données carte.
- Pagination produits, catégories, images upload, variantes, coupons.
- Migrations DB (Flask-Migrate/SQLAlchemy) et ORM à la place de requêtes brutes.
- Séparer fichiers en blueprints, ajouter tests unitaires, dockerisation, logs structurés, rate limiting, etc.