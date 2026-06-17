import sqlite3
import os
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('instance/coworking.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Créer le dossier instance s'il n'existe pas
    os.makedirs('instance', exist_ok=True)
    
    conn = get_db_connection()
    
    # Créer la table des utilisateurs
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Créer la table des salles
    conn.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            capacity INTEGER NOT NULL,
            price_per_hour REAL NOT NULL,
            equipment TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Créer la table des réservations
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (room_id) REFERENCES rooms (id)
        )
    ''')
    
    # Insérer un administrateur par défaut (mot de passe: admin123)
    admin_exists = conn.execute('SELECT * FROM users WHERE email = ?', ('admin@coworking.com',)).fetchone()
    if not admin_exists:
        conn.execute('''
            INSERT INTO users (username, email, password, is_admin)
            VALUES (?, ?, ?, ?)
        ''', ('Administrateur', 'admin@coworking.com', 'admin123', 1))
    
    # Insérer des salles par défaut
    rooms_count = conn.execute('SELECT COUNT(*) as count FROM rooms').fetchone()['count']
    if rooms_count == 0:
        default_rooms = [
            ('Salle Réunion A', 'Salle de réunion équipée d\'un vidéoprojecteur', 8, 25.0, 'Vidéoprojecteur, Tableau blanc, Wi-Fi'),
            ('Salle Réunion B', 'Salle de réunion avec écran TV', 6, 20.0, 'Écran TV 55", Tableau blanc, Wi-Fi'),
            ('Bureau Privé', 'Bureau individuel fermé', 1, 15.0, 'Bureau, Chaise, Wi-Fi, Prises électriques'),
            ('Open Space', 'Espace de coworking partagé', 20, 10.0, 'Wi-Fi, Cafetière, Imprimante'),
            ('Salle Créative', 'Salle pour brainstormings et ateliers', 12, 30.0, 'Tableau blanc interactif, Post-its, Wi-Fi')
        ]
        
        for room in default_rooms:
            conn.execute('''
                INSERT INTO rooms (name, description, capacity, price_per_hour, equipment)
                VALUES (?, ?, ?, ?, ?)
            ''', room)
    
    conn.commit()
    conn.close()
