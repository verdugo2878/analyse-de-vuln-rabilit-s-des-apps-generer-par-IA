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
