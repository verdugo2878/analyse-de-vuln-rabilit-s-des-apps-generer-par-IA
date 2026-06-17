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
