pip install Flask Flask-SQLAlchemy Flask-Login Flask-WTF

# --- bloc suivant fusionné ---
CREATE TABLE produits (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    description TEXT,
    prix REAL NOT NULL,
    stock INTEGER NOT NULL
);

CREATE TABLE commandes (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL,
    adresse TEXT NOT NULL,
    paiement TEXT NOT NULL,
    total REAL NOT NULL,
    date DATE NOT NULL
);

CREATE TABLE lignes_commande (
    id INTEGER PRIMARY KEY,
    commande_id INTEGER NOT NULL,
    produit_id INTEGER NOT NULL,
    quantite INTEGER NOT NULL,
    FOREIGN KEY (commande_id) REFERENCES commandes (id),
    FOREIGN KEY (produit_id) REFERENCES produits (id)
);

CREATE TABLE clients (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    email TEXT NOT NULL,
    mot_de_passe TEXT NOT NULL
);
