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
