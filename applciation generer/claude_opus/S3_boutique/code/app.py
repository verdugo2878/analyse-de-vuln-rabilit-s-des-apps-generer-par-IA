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
