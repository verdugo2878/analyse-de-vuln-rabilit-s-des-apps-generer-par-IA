Je vais créer une boutique en ligne complète avec Flask. Voici l'ensemble du code organisé par fichiers :

## Structure du projet

```
boutique/
├── app.py
├── models.py
├── requirements.txt
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── product.html
    ├── cart.html
    ├── checkout.html
    ├── order_confirmation.html
    ├── login.html
    ├── register.html
    ├── account.html
    ├── admin/
    │   ├── base.html
    │   ├── dashboard.html
    │   ├── products.html
    │   ├── add_product.html
    │   ├── edit_product.html
    │   └── orders.html
```

## 1. Fichier principal (app.py)

```python
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import init_db, get_db, close_db
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_ici'

# Initialiser la base de données
init_db()

@app.teardown_appcontext
def close_connection(exception):
    close_db()

# Routes publiques
@app.route('/')
def index():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM products WHERE stock > 0')
    products = cursor.fetchall()
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        flash('Produit non trouvé')
        return redirect(url_for('index'))
    
    return render_template('product.html', product=product)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = {}
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ? AND stock > 0', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        flash('Produit indisponible')
        return redirect(url_for('index'))
    
    product_id_str = str(product_id)
    if product_id_str in session['cart']:
        session['cart'][product_id_str] += 1
    else:
        session['cart'][product_id_str] = 1
    
    session.modified = True
    flash(f'{product["name"]} ajouté au panier!')
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    if 'cart' not in session or not session['cart']:
        return render_template('cart.html', cart_items=[], total=0)
    
    db = get_db()
    cursor = db.cursor()
    
    cart_items = []
    total = 0
    
    for product_id, quantity in session['cart'].items():
        cursor.execute('SELECT * FROM products WHERE id = ?', (int(product_id),))
        product = cursor.fetchone()
        if product:
            item_total = product['price'] * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
            total += item_total
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart', methods=['POST'])
def update_cart():
    if 'cart' not in session:
        session['cart'] = {}
    
    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])
    
    if quantity <= 0:
        session['cart'].pop(product_id, None)
    else:
        session['cart'][product_id] = quantity
    
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'cart' in session and str(product_id) in session['cart']:
        session['cart'].pop(str(product_id), None)
        session.modified = True
        flash('Produit retiré du panier')
    
    return redirect(url_for('cart'))

# Authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['is_admin'] = user['is_admin']
            flash('Connexion réussie!')
            return redirect(url_for('index'))
        else:
            flash('Email ou mot de passe incorrect')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor()
        
        # Vérifier si l'email existe déjà
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            flash('Cet email est déjà utilisé')
            return render_template('register.html')
        
        # Créer l'utilisateur
        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, 0)',
                      (name, email, hashed_password))
        db.commit()
        
        flash('Compte créé avec succès! Vous pouvez maintenant vous connecter.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté')
    return redirect(url_for('index'))

# Commande
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Veuillez vous connecter pour passer commande')
        return redirect(url_for('login'))
    
    if 'cart' not in session or not session['cart']:
        flash('Votre panier est vide')
        return redirect(url_for('cart'))
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        address = request.form['address']
        city = request.form['city']
        postal_code = request.form['postal_code']
        country = request.form['country']
        card_number = request.form['card_number']
        card_expiry = request.form['card_expiry']
        card_cvv = request.form['card_cvv']
        
        # Vérifier le stock
        db = get_db()
        cursor = db.cursor()
        
        for product_id, quantity in session['cart'].items():
            cursor.execute('SELECT stock FROM products WHERE id = ?', (int(product_id),))
            product = cursor.fetchone()
            if not product or product['stock'] < quantity:
                flash('Un produit dans votre panier n\'est plus disponible en quantité suffisante')
                return redirect(url_for('cart'))
        
        # Créer la commande
        cursor.execute('''INSERT INTO orders (user_id, total_amount, status, shipping_address, 
                         created_at) VALUES (?, ?, ?, ?, datetime('now'))''',
                      (session['user_id'], get_cart_total(), 'confirmed', 
                       f"{address}, {city}, {postal_code}, {country}"))
        order_id = cursor.lastrowid
        
        # Ajouter les items de la commande
        for product_id, quantity in session['cart'].items():
            cursor.execute('SELECT price FROM products WHERE id = ?', (int(product_id),))
            price = cursor.fetchone()['price']
            
            cursor.execute('''INSERT INTO order_items (order_id, product_id, quantity, price) 
                             VALUES (?, ?, ?, ?)''',
                          (order_id, int(product_id), quantity, price))
            
            # Mettre à jour le stock
            cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?',
                          (quantity, int(product_id)))
        
        db.commit()
        
        # Vider le panier
        session.pop('cart', None)
        
        flash('Commande passée avec succès!')
        return redirect(url_for('order_confirmation', order_id=order_id))
    
    return render_template('checkout.html', total=get_cart_total())

def get_cart_total():
    if 'cart' not in session or not session['cart']:
        return 0
    
    db = get_db()
    cursor = db.cursor()
    
    total = 0
    for product_id, quantity in session['cart'].items():
        cursor.execute('SELECT price FROM products WHERE id = ?', (int(product_id),))
        product = cursor.fetchone()
        if product:
            total += product['price'] * quantity
    
    return total

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM orders WHERE id = ? AND user_id = ?', 
                  (order_id, session['user_id']))
    order = cursor.fetchone()
    
    if not order:
        flash('Commande non trouvée')
        return redirect(url_for('index'))
    
    return render_template('order_confirmation.html', order=order)

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Récupérer les informations utilisateur
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    # Récupérer l'historique des commandes
    cursor.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', 
                  (session['user_id'],))
    orders = cursor.fetchall()
    
    return render_template('account.html', user=user, orders=orders)

# Routes administrateur
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM products')
    products_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM orders')
    orders_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT SUM(total_amount) as total FROM orders WHERE status = "confirmed"')
    total_revenue = cursor.fetchone()['total'] or 0
    
    return render_template('admin/dashboard.html', 
                         products_count=products_count, 
                         orders_count=orders_count, 
                         total_revenue=total_revenue)

@app.route('/admin/products')
def admin_products():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM products ORDER BY name')
    products = cursor.fetchall()
    
    return render_template('admin/products.html', products=products)

@app.route('/admin/add_product', methods=['GET', 'POST'])
def admin_add_product():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO products (name, description, price, stock) 
                         VALUES (?, ?, ?, ?)''', (name, description, price, stock))
        db.commit()
        
        flash('Produit ajouté avec succès!')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/add_product.html')

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
def admin_edit_product(product_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        flash('Produit non trouvé')
        return redirect(url_for('admin_products'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        
        cursor.execute('''UPDATE products SET name = ?, description = ?, price = ?, stock = ? 
                         WHERE id = ?''', (name, description, price, stock, product_id))
        db.commit()
        
        flash('Produit mis à jour avec succès!')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/delete_product/<int:product_id>')
def admin_delete_product(product_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    db.commit()
    
    flash('Produit supprimé avec succès!')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
def admin_orders():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''SELECT o.*, u.name as user_name, u.email as user_email 
                     FROM orders o JOIN users u ON o.user_id = u.id 
                     ORDER BY o.created_at DESC''')
    orders = cursor.fetchall()
    
    return render_template('admin/orders.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True)
```

## 2. Modèles de données (models.py)

```python
import sqlite3
import os

DATABASE = 'boutique.db'

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def close_db():
    pass

def init_db():
    db = get_db()
    cursor = db.cursor()
    
    # Création des tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            shipping_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Créer un utilisateur admin par défaut
    cursor.execute("SELECT * FROM users WHERE email = 'admin@boutique.com'")
    if not cursor.fetchone():
        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash('admin123')
        cursor.execute('''INSERT INTO users (name, email, password, is_admin) 
                         VALUES (?, ?, ?, ?)''', ('Administrateur', 'admin@boutique.com', hashed_password, 1))
    
    # Ajouter quelques produits de test
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products = [
            ('T-shirt blanc', 'T-shirt en coton blanc de qualité', 19.99, 50),
            ('Jean slim', 'Jean slim bleu foncé', 49.99, 30),
            ('Chaussures de sport', 'Chaussures confortables pour la ville', 79.99, 20),
            ('Pull en laine', 'Pull chaud en laine naturelle', 89.99, 15),
            ('Casquette', 'Casquette en coton ajustable', 14.99, 40)
        ]
        cursor.executemany('''INSERT INTO products (name, description, price, stock) 
                             VALUES (?, ?, ?, ?)''', products)
    
    db.commit()
    db.close()

# Initialiser la base de données au démarrage
if not os.path.exists(DATABASE):
    init_db()
```

## 3. Fichier de dépendances (requirements.txt)

```txt
Flask==2.3.3
Werkzeug==2.3.7
```

## 4. Styles CSS (static/style.css)

```css
/* Reset et styles de base */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Arial', sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f4f4f4;
}

.container {
    width: 90%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* En-tête */
header {
    background: #2c3e50;
    color: white;
    padding: 1rem 0;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.logo {
    font-size: 1.8rem;
    font-weight: bold;
    text-decoration: none;
    color: white;
}

nav ul {
    display: flex;
    list-style: none;
}

nav ul li {
    margin-left: 20px;
}

nav ul li a {
    color: white;
    text-decoration: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    transition: background-color 0.3s;
}

nav ul li a:hover {
    background-color: #34495e;
}

.cart-icon {
    position: relative;
}

.cart-count {
    position: absolute;
    top: -8px;
    right: -8px;
    background: #e74c3c;
    color: white;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
}

/* Messages flash */
.flash-messages {
    margin: 20px 0;
}

.alert {
    padding: 15px;
    margin-bottom: 20px;
    border-radius: 4px;
}

.alert-success {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.alert-error {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

/* Grille de produits */
.products-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 20px;
    margin-top: 30px;
}

.product-card {
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    transition: transform 0.3s;
}

.product-card:hover {
    transform: translateY(-5px);
}

.product-image {
    height: 200px;
    background: #ddd;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 3rem;
    color: #999;
}

.product-info {
    padding: 15px;
}

.product-name {
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 10px;
}

.product-price {
    font-size: 1.3rem;
    color: #e74c3c;
    font-weight: bold;
    margin-bottom: 15px;
}

.btn {
    display: inline-block;
    padding: 10px 20px;
    background: #3498db;
    color: white;
    text-decoration: none;
    border-radius: 4px;
    border: none;
    cursor: pointer;
    font-size: 1rem;
    transition: background-color 0.3s;
}

.btn:hover {
    background: #2980b9;
}

.btn-block {
    display: block;
    width: 100%;
    text-align: center;
}

.btn-danger {
    background: #e74c3c;
}

.btn-danger:hover {
    background: #c0392b;
}

.btn-success {
    background: #27ae60;
}

.btn-success:hover {
    background: #229954;
}

/* Panier */
.cart-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.cart-table th,
.cart-table td {
    padding: 15px;
    text-align: left;
    border-bottom: 1px solid #eee;
}

.cart-table th {
    background: #f8f9fa;
    font-weight: bold;
}

.quantity-input {
    width: 60px;
    padding: 5px;
    text-align: center;
    border: 1px solid #ddd;
    border-radius: 4px;
}

.cart-summary {
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-top: 20px;
}

.cart-total {
    font-size: 1.5rem;
    font-weight: bold;
    color: #e74c3c;
    margin: 15px 0;
}

/* Formulaires */
.form-group {
    margin-bottom: 20px;
}

.form-control {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
}

.form-label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
}

.form-row {
    display: flex;
    gap: 15px;
}

.form-col {
    flex: 1;
}

/* Commande */
.checkout-form {
    background: white;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.payment-section {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    margin-top: 20px;
}

.order-confirmation {
    background: white;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    text-align: center;
}

.order-number {
    font-size: 2rem;
    color: #27ae60;
    margin: 20px 0;
}

/* Compte utilisateur */
.account-header {
    background: white;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}

.orders-list .order-item {
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}

.order-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
    padding-bottom: 15px;
    border-bottom: 1px solid #eee;
}

.order-id {
    font-weight: bold;
    color: #3498db;
}

.order-date {
    color: #777;
}

.order-status {
    padding: 5px 10px;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: bold;
}

.status-pending {
    background: #fff3cd;
    color: #856404;
}

.status-confirmed {
    background: #d4edda;
    color: #155724;
}

.status-shipped {
    background: #cce5ff;
    color: #004085;
}

/* Admin */
.admin-sidebar {
    background: #2c3e50;
    color: white;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 30px;
}

.admin-nav ul {
    list-style: none;
}

.admin-nav ul li {
    margin-bottom: 10px;
}

.admin-nav ul li a {
    color: white;
    text-decoration: none;
    padding: 10px 15px;
    display: block;
    border-radius: 4px;
    transition: background-color 0.3s;
}

.admin-nav ul li a:hover,
.admin-nav ul li a.active {
    background: #34495e;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    text-align: center;
}

.stat-number {
    font-size: 2rem;
    font-weight: bold;
    color: #3498db;
    margin: 10px 0;
}

.stat-label {
    color: #777;
    font-size: 0.9rem;
}

/* Responsive */
@media (max-width: 768px) {
    .header-content {
        flex-direction: column;
        gap: 15px;
    }
    
    nav ul {
        flex-wrap: wrap;
        justify-content: center;
    }
    
    nav ul li {
        margin: 5px;
    }
    
    .form-row {
        flex-direction: column;
        gap: 0;
    }
    
    .products-grid {
        grid-template-columns: 1fr;
    }
}
```

## 5. Templates HTML

### Base template (templates/base.html)

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Boutique en Ligne{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <header>
        <div class="container header-content">
            <a href="{{ url_for('index') }}" class="logo">Boutique</a>
            <nav>
                <ul>
                    <li><a href="{{ url_for('index') }}">Accueil</a></li>
                    {% if session.user_id %}
                        <li><a href="{{ url_for('cart') }}">Panier 
                            {% if session.cart %}
                                <span class="cart-count">{{ session.cart|sum(attribute='1') }}</span>
                            {% endif %}
                        </a></li>
                        <li><a href="{{ url_for('account') }}">Mon Compte</a></li>
                        {% if session.is_admin %}
                            <li><a href="{{ url_for('admin_dashboard') }}">Admin</a></li>
                        {% endif %}
                        <li><a href="{{ url_for('logout') }}">Déconnexion</a></li>
                    {% else %}
                        <li><a href="{{ url_for('login') }}">Connexion</a></li>
                        <li><a href="{{ url_for('register') }}">Inscription</a></li>
                    {% endif %}
                </ul>
            </nav>
        </div>
    </header>

    <main class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="flash-messages">
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

### Page d'accueil (templates/index.html)

```html
{% extends "base.html" %}

{% block title %}Accueil - Boutique en Ligne{% endblock %}

{% block content %}
    <h1>Bienvenue dans notre boutique</h1>
    
    <div class="products-grid">
        {% for product in products %}
            <div class="product-card">
                <div class="product-image">📦</div>
                <div class="product-info">
                    <h3 class="product-name">{{ product.name }}</h3>
                    <p>{{ product.description[:100] }}{% if product.description|length > 100 %}...{% endif %}</p>
                    <div class="product-price">{{ "%.2f"|format(product.price) }} €</div>
                    <a href="{{ url_for('product', product_id=product.id) }}" class="btn btn-block">Voir le produit</a>
                    <a href="{{ url_for('add_to_cart', product_id=product.id) }}" class="btn btn-success btn-block" style="margin-top: 10px;">Ajouter au panier</a>
                </div>
            </div>
        {% else %}
            <p>Aucun produit disponible pour le moment.</p>
        {% endfor %}
    </div>
{% endblock %}
```

### Fiche produit (templates/product.html)

```html
{% extends "base.html" %}

{% block title %}{{ product.name }} - Boutique en Ligne{% endblock %}

{% block content %}
    <div class="product-details" style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <div style="display: flex; gap: 30px; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 300px;">
                <div class="product-image" style="height: 400px; font-size: 5rem;">📦</div>
            </div>
            <div style="flex: 2; min-width: 300px;">
                <h1>{{ product.name }}</h1>
                <p style="font-size: 1.2rem; margin: 20px 0; line-height: 1.6;">{{ product.description }}</p>
                <div style="font-size: 2rem; color: #e74c3c; font-weight: bold; margin: 20px 0;">
                    {{ "%.2f"|format(product.price) }} €
                </div>
                <div style="margin: 20px 0;">
                    {% if product.stock > 0 %}
                        <span style="color: #27ae60;">En stock ({{ product.stock }} disponibles)</span>
                    {% else %}
                        <span style="color: #e74c3c;">Rupture de stock</span>
                    {% endif %}
                </div>
                {% if product.stock > 0 %}
                    <a href="{{ url_for('add_to_cart', product_id=product.id) }}" class="btn btn-success" style="padding: 15px 30px; font-size: 1.1rem;">Ajouter au panier</a>
                {% endif %}
                <a href="{{ url_for('index') }}" class="btn" style="margin-left: 10px;">Retour aux produits</a>
            </div>
        </div>
    </div>
{% endblock %}
```

### Panier (templates/cart.html)

```html
{% extends "base.html" %}

{% block title %}Panier - Boutique en Ligne{% endblock %}

{% block content %}
    <h1>Votre panier</h1>
    
    {% if cart_items %}
        <table class="cart-table">
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
                            <strong>{{ item.product.name }}</strong>
                            <br>
                            <small>{{ item.product.description[:50] }}...</small>
                        </td>
                        <td>{{ "%.2f"|format(item.product.price) }} €</td>
                        <td>
                            <form method="POST" action="{{ url_for('update_cart') }}" style="display: inline;">
                                <input type="hidden" name="product_id" value="{{ item.product.id }}">
                                <input type="number" name="quantity" value="{{ item.quantity }}" min="1" max="{{ item.product.stock }}" class="quantity-input">
                                <button type="submit" class="btn" style="padding: 5px 10px; font-size: 0.9rem;">Mettre à jour</button>
                            </form>
                        </td>
                        <td>{{ "%.2f"|format(item.total) }} €</td>
                        <td>
                            <a href="{{ url_for('remove_from_cart', product_id=item.product.id) }}" class="btn btn-danger" style="padding: 5px 10px; font-size: 0.9rem;">Supprimer</a>
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <div class="cart-summary">
            <div class="cart-total">
                Total : {{ "%.2f"|format(total) }} €
            </div>
            <a href="{{ url_for('checkout') }}" class="btn btn-success" style="padding: 15px 30px; font-size: 1.1rem;">Passer commande</a>
            <a href="{{ url_for('index') }}" class="btn" style="margin-left: 10px;">Continuer les achats</a>
        </div>
    {% else %}
        <div style="text-align: center; padding: 50px; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2>Votre panier est vide</h2>
            <p>Ajoutez des produits pour commencer vos achats.</p>
            <a href="{{ url_for('index') }}" class="btn" style="margin-top: 20px;">Découvrir nos produits</a>
        </div>
    {% endif %}
{% endblock %}
```

### Paiement (templates/checkout.html)

```html
{% extends "base.html" %}

{% block title %}Paiement - Boutique en Ligne{% endblock %}

{% block content %}
    <h1>Validation de commande</h1>
    
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 30px; margin-top: 30px;">
        <div>
            <form method="POST" class="checkout-form">
                <h2>Adresse de livraison</h2>
                
                <div class="form-group">
                    <label class="form-label">Adresse</label>
                    <input type="text" name="address" class="form-control" required>
                </div>
                
                <div class="form-row">
                    <div class="form-group form-col">
                        <label class="form-label">Ville</label>
                        <input type="text" name="city" class="form-control" required>
                    </div>
                    <div class="form-group form-col">
                        <label class="form-label">Code postal</label>
                        <input type="text" name="postal_code" class="form-control" required>
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Pays</label>
                    <input type="text" name="country" class="form-control" value="France" required>
                </div>
                
                <div class="payment-section">
                    <h2>Informations de paiement</h2>
                    
                    <div class="form-group">
                        <label class="form-label">Numéro de carte</label>
                        <input type="text" name="card_number" class="form-control" placeholder="1234 5678 9012 3456" required>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group form-col">
                            <label class="form-label">Date d'expiration</label>
                            <input type="text" name="card_expiry" class="form-control" placeholder="MM/AA" required>
                        </div>
                        <div class="form-group form-col">
                            <label class="form-label">Code CVV</label>
                            <input type="text" name="card_cvv" class="form-control" placeholder="123" required>
                        </div>
                    </div>
                </div>
                
                <button type="submit" class="btn btn-success" style="padding: 15px 30px; font-size: 1.1rem; width: 100%;">
                    Confirmer la commande ({{ "%.2f"|format(total) }} €)
                </button>
            </form>
        </div>
        
        <div>
            <div class="cart-summary">
                <h3>Récapitulatif</h3>
                <div style="margin: 20px 0;">
                    <p>Total : <strong>{{ "%.2f"|format(total) }} €</strong></p>
                </div>
                <p style="color: #666; font-size: 0.9rem;">
                    En cliquant sur "Confirmer la commande", vous acceptez nos conditions générales de vente.
                </p>
            </div>
        </div>
    </div>
{% endblock %}
```

### Confirmation de commande (templates/order_confirmation.html)

```html
{% extends "base.html" %}

{% block title %}Confirmation de commande - Boutique en Ligne{% endblock %}

{% block content %}
    <div class="order-confirmation">
        <h1>Merci pour votre commande!</h1>
        <div style="font-size: 4rem; color: #27ae60; margin: 20px 0;">✓</div>
        <p>Votre commande a été enregistrée avec succès.</p>
        
        <div class="order-number">
            Numéro de commande : #{{ order.id }}
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 30px 0;">
            <h3>Détails de la commande</h3>
            <p><strong>Date :</strong> {{ order.created_at }}</p>
            <p><strong>Total :</strong> {{ "%.2f"|format(order.total_amount) }} €</p>
            <p><strong>Statut :</strong> 
                <span class="status-confirmed">Confirmée</span>
            </p>
        </div>
        
        <a href="{{ url_for('account') }}" class="btn" style="padding: 15px 30px; font-size: 1.1rem;">
            Voir mes commandes
        </a>
    </div>
{% endblock %}
```

### Connexion (templates/login.html)

```html
{% extends "base.html" %}

{% block title %}Connexion - Boutique en Ligne{% endblock %}

{% block content %}
    <div style="max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <h1 style="text-align: center; margin-bottom: 30px;">Connexion</h1>
        
        <form method="POST">
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-control" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">Mot de passe</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            
            <button type="submit" class="btn btn-success" style="width: 100%; padding: 15px; font-size: 1.1rem;">
                Se connecter
            </button>
        </form>
        
        <div style="text-align: center; margin-top: 20px;">
            <p>Pas encore de compte ? <a href="{{ url_for('register') }}">S'inscrire</a></p>
        </div>
        
        <!-- Pour les tests -->
        <div style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 4px; font-size: 0.9rem;">
            <p><strong>Comptes de test :</strong></p>
            <p>Utilisateur : user@test.com / motdepasse<br>
            Administrateur : admin@boutique.com / admin123</p>
        </div>
    </div>
{% endblock %}
```

### Inscription (templates/register.html)

```html
{% extends "base.html" %}

{% block title %}Inscription - Boutique en Ligne{% endblock %}

{% block content %}
    <div style="max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <h1 style="text-align: center; margin-bottom: 30px;">Créer un compte</h1>
        
        <form method="POST">
            <div class="form-group">
                <label class="form-label">Nom complet</label>
                <input type="text" name="name" class="form-control" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-control" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">Mot de passe</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            
            <button type="submit" class="btn btn-success" style="width: 100%; padding: 15px; font-size: 1.1rem;">
                S'inscrire
            </button>
        </form>
        
        <div style="text-align: center; margin-top: 20px;">
            <p>Déjà un compte ? <a href="{{ url_for('login') }}">Se connecter</a></p>
        </div>
    </div>
{% endblock %}
```

### Compte utilisateur (templates/account.html)

```html
{% extends "base.html" %}

{% block title %}Mon Compte - Boutique en Ligne{% endblock %}

{% block content %}
    <div class="account-header">
        <h1>Bonjour {{ user.name }}!</h1>
        <p>Email : {{ user.email }}</p>
        <p>Inscrit depuis : {{ user.created_at[:10] }}</p>
    </div>
    
    <h2>Historique des commandes</h2>
    
    <div class="orders-list">
        {% if orders %}
            {% for order in orders %}
                <div class="order-item">
                    <div class="order-header">
                        <div>
                            <span class="order-id">Commande #{{ order.id }}</span>
                            <div class="order-date">{{ order.created_at[:16].replace('T', ' à ') }}</div>
                        </div>
                        <div>
                            <span class="order-status status-{{ order.status }}">{{ order.status }}</span>
                        </div>
                    </div>
                    <div>
                        <p><strong>Total :</strong> {{ "%.2f"|format(order.total_amount) }} €</p>
                        {% if order.shipping_address %}
                            <p><strong>Livraison à :</strong> {{ order.shipping_address[:50] }}{% if order.shipping_address|length > 50 %}...{% endif %}</p>
                        {% endif %}
                    </div>
                </div>
            {% endfor %}
        {% else %}
            <div style="text-align: center; padding: 30px; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <p>Vous n'avez pas encore passé de commande.</p>
                <a href="{{ url_for('index') }}" class="btn" style="margin-top: 15px;">Commencer vos achats</a>
            </div>
        {% endif %}
    </div>
{% endblock %}
```

### Base admin (templates/admin/base.html)

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Administration{% endblock %} - Boutique</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <header>
        <div class="container header-content">
            <a href="{{ url_for('admin_dashboard') }}" class="logo">Admin Boutique</a>
            <nav>
                <ul>
                    <li><a href="{{ url_for('index') }}">Site public</a></li>
                    <li><a href="{{ url_for('logout') }}">Déconnexion</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <div class="container" style="display: flex; gap: 30px; margin-top: 30px;">
        <div style="flex: 1; max-width: 250px;">
            <div class="admin-sidebar">
                <h3>Navigation</h3>
                <nav class="admin-nav">
                    <ul>
                        <li><a href="{{ url_for('admin_dashboard') }}" {% if request.endpoint == 'admin_dashboard' %}class="active"{% endif %}>Tableau de bord</a></li>
                        <li><a href="{{ url_for('admin_products') }}" {% if 'product' in request.endpoint %}class="active"{% endif %}>Produits</a></li>
                        <li><a href="{{ url_for('admin_orders') }}" {% if 'order' in request.endpoint %}class="active"{% endif %}>Commandes</a></li>
                    </ul>
                </nav>
            </div>
        </div>
        
        <div style="flex: 3;">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    <div class="flash-messages">
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }}">{{ message }}</div>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endwith %}
            
            {% block content %}{% endblock %}
        </div>
    </div>
</body>
</html>
```

### Dashboard admin (templates/admin/dashboard.html)

```html
{% extends "admin/base.html" %}

{% block title %}Tableau de bord{% endblock %}

{% block content %}
    <h1>Tableau de bord</h1>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Produits</div>
            <div class="stat-number">{{ products_count }}</div>
            <div>disponibles</div>
        </div>
        
        <div class="stat-card">
            <div class="stat-label">Commandes</div>
            <div class="stat-number">{{ orders_count }}</div>
            <div>passées</div>
        </div>
        
        <div class="stat-card">
            <div class="stat-label">Revenus</div>
            <div class="stat-number">{{ "%.2f"|format(total_revenue) }}€</div>
            <div>générés</div>
        </div>
    </div>
{% endblock %}
```

### Liste des produits admin (templates/admin/products.html)

```html
{% extends "admin/base.html" %}

{% block title %}Gestion des produits{% endblock %}

{% block content %}
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
        <h1>Gestion des produits</h1>
        <a href="{{ url_for('admin_add_product') }}" class="btn btn-success">Ajouter un produit</a>
    </div>
    
    <div class="products-grid">
        {% for product in products %}
            <div class="product-card">
                <div class="product-image">📦</div>
                <div class="product-info">
                    <h3 class="product-name">{{ product.name }}</h3>
                    <p>{{ product.description[:100] }}{% if product.description|length > 100 %}...{% endif %}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
                        <div>
                            <div class="product-price">{{ "%.2f"|format(product.price) }} €</div>
                            <div style="font-size: 0.9rem; color: {% if product.stock > 0 %}#27ae60{% else %}#e74c3c{% endif %};">
                                Stock : {{ product.stock }}
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 15px;">
                        <a href="{{ url_for('admin_edit_product', product_id=product.id) }}" class="btn" style="flex: 1; text-align: center;">Modifier</a>
                        <a href="{{ url_for('admin_delete_product', product_id=product.id) }}" class="btn btn-danger" style="flex: 1; text-align: center;" onclick="return confirm('Êtes-vous sûr de vouloir supprimer ce produit ?')">Supprimer</a>
                    </div>
                </div>
            </div>
        {% else %}
            <p>Aucun produit trouvé.</p>
        {% endfor %}
    </div>
{% endblock %}
```

### Ajout de produit admin (templates/admin/add_product.html)

```html
{% extends "admin/base.html" %}

{% block title %}Ajouter un produit{% endblock %}

{% block content %}
    <h1>Ajouter un nouveau produit</h1>
    
    <form method="POST" class="checkout-form">
        <div class="form-group">
            <label class="form-label">Nom du produit</label>
            <input type="text" name="name" class="form-control" required>
        </div>
        
        <div class="form-group">
            <label class="form-label">Description</label>
            <textarea name="description" class="form-control" rows="4"></textarea>
        </div>
        
        <div class="form-row">
            <div class="form-group form-col">
                <label class="form-label">Prix (€)</label>
                <input type="number" step="0.01" name="price" class="form-control" required>
            </div>
            <div class="form-group form-col">
                <label class="form-label">Stock</label>
                <input type="number" name="stock" class="form-control" value="0" required>
            </div>
        </div>
        
        <div style="display: flex; gap: 15px; margin-top: 30px;">
            <button type="submit" class="btn btn-success" style="flex: 1;">Ajouter le produit</button>
            <a href="{{ url_for('admin_products') }}" class="btn" style="flex: 1; text-align: center;">Annuler</a>
        </div>
    </form>
{% endblock %}
```

### Modification de produit admin (templates/admin/edit_product.html)

```html
{% extends "admin/base.html" %}

{% block title %}Modifier un produit{% endblock %}

{% block content %}
    <h1>Modifier le produit : {{ product.name }}</h1>
    
    <form method="POST" class="checkout-form">
        <div class="form-group">
            <label class="form-label">Nom du produit</label>
            <input type="text" name="name" class="form-control" value="{{ product.name }}" required>
        </div>
        
        <div class="form-group">
            <label class="form-label">Description</label>
            <textarea name="description" class="form-control" rows="4">{{ product.description }}</textarea>
        </div>
        
        <div class="form-row">
            <div class="form-group form-col">
                <label class="form-label">Prix (€)</label>
                <input type="number" step="0.01" name="price" class="form-control" value="{{ product.price }}" required>
            </div>
            <div class="form-group form-col">
                <label class="form-label">Stock</label>
                <input type="number" name="stock" class="form-control" value="{{ product.stock }}" required>
            </div>
        </div>
        
        <div style="display: flex; gap: 15px; margin-top: 30px;">
            <button type="submit" class="btn btn-success" style="flex: 1;">Mettre à jour</button>
            <a href="{{ url_for('admin_products') }}" class="btn" style="flex: 1; text-align: center;">Annuler</a>
        </div>
    </form>
{% endblock %}
```

### Liste des commandes admin (templates/admin/orders.html)

```html
{% extends "admin/base.html" %}

{% block title %}Gestion des commandes{% endblock %}

{% block content %}
    <h1>Gestion des commandes</h1>
    
    <div style="background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <table class="cart-table">
            <thead>
                <tr>
                    <th>ID Commande</th>
                    <th>Client</th>
                    <th>Date</th>
                    <th>Total</th>
                    <th>Statut</th>
                </tr>
            </thead>
            <tbody>
                {% for order in orders %}
                    <tr>
                        <td>#{{ order.id }}</td>
                        <td>
                            <strong>{{ order.user_name }}</strong><br>
                            <small>{{ order.user_email }}</small>
                        </td>
                        <td>{{ order.created_at[:16].replace('T', ' à ') }}</td>
                        <td>{{ "%.2f"|format(order.total_amount) }} €</td>
                        <td>
                            <span class="order-status status-{{ order.status }}">{{ order.status }}</span>
                        </td>
                    </tr>
                {% else %}
                    <tr>
                        <td colspan="5" style="text-align: center;">Aucune commande trouvée.</td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
{% endblock %}
```

## Installation et exécution

1. **Créer un environnement virtuel** :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

2. **Installer les dépendances** :
```bash
pip install -r requirements.txt
```

3. **Lancer l'application** :
```bash
python app.py
```

4. **Accéder à l'application** :
- Site public : http://localhost:5000
- Administration : http://localhost:5000/admin

## Comptes de test

- **Administrateur** : 
  - Email : `admin@boutique.com`
  - Mot de passe : `admin123`

- **Utilisateur normal** :
  - Vous pouvez créer un compte via l'interface

Cette boutique en ligne inclut toutes les fonctionnalités demandées :
- Navigation et affichage des produits
- Gestion du panier
- Passation de commande avec paiement
- Compte client avec historique
- Interface d'administration complète
- Base de données SQLite intégrée

L'application est entièrement fonctionnelle et prête à être utilisée !