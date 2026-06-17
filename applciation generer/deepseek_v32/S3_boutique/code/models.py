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
