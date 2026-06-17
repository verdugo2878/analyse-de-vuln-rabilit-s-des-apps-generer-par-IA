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
