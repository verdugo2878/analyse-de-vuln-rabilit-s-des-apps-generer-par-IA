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
