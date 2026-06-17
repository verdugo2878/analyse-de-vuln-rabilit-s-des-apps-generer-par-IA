Je vais créer une application Flask complète de réservation de salles de coworking avec toutes les fonctionnalités demandées.

## Structure du projet

```
coworking_reservation/
├── app.py
├── database.py
├── models.py
├── requirements.txt
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── rooms.html
│   ├── book.html
│   ├── my_bookings.html
│   ├── admin_bookings.html
│   ├── admin_rooms.html
│   └── add_room.html
└── instance/
    └── coworking.db
```

## 1. Fichier requirements.txt

```txt
Flask==3.0.0
Flask-Login==0.6.3
Werkzeug==3.0.1
```

## 2. Fichier app.py

```python
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import sqlite3
from database import init_db, get_db_connection
from models import User, Room, Booking

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_cle_secrete_ici'
app.config['DATABASE'] = 'instance/coworking.db'

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['email'], user['is_admin'])
    return None

# Routes principales
@app.route('/')
def index():
    return render_template('index.html')

# Routes d'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and user['password'] == password:  # En production, utilisez bcrypt
            user_obj = User(user['id'], user['username'], user['email'], user['is_admin'])
            login_user(user_obj)
            flash('Connexion réussie!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email ou mot de passe incorrect', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        
        # Vérifier si l'email existe déjà
        existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            flash('Cet email est déjà utilisé', 'error')
            conn.close()
            return redirect(url_for('register'))
        
        # Créer le nouvel utilisateur
        conn.execute('INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)',
                    (username, email, password, 0))
        conn.commit()
        conn.close()
        
        flash('Compte créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('index'))

# Routes pour les salles
@app.route('/rooms')
def rooms():
    conn = get_db_connection()
    rooms = conn.execute('SELECT * FROM rooms WHERE is_active = 1').fetchall()
    conn.close()
    return render_template('rooms.html', rooms=rooms)

@app.route('/api/available_slots')
def available_slots():
    room_id = request.args.get('room_id')
    date = request.args.get('date')
    
    if not room_id or not date:
        return jsonify({'error': 'Paramètres manquants'}), 400
    
    conn = get_db_connection()
    
    # Récupérer les créneaux déjà réservés
    bookings = conn.execute('''
        SELECT start_time, end_time FROM bookings 
        WHERE room_id = ? AND DATE(start_time) = ? AND status = 'confirmed'
    ''', (room_id, date)).fetchall()
    
    # Récupérer les horaires d'ouverture de la salle
    room = conn.execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()
    conn.close()
    
    if not room:
        return jsonify({'error': 'Salle non trouvée'}), 404
    
    # Générer tous les créneaux disponibles (9h-18h, par tranches d'1 heure)
    available_slots = []
    start_hour = 9
    end_hour = 18
    
    for hour in range(start_hour, end_hour):
        slot_start = f"{date} {hour:02d}:00:00"
        slot_end = f"{date} {hour+1:02d}:00:00"
        
        # Vérifier si le créneau est déjà réservé
        is_available = True
        for booking in bookings:
            booking_start = datetime.fromisoformat(booking['start_time'])
            booking_end = datetime.fromisoformat(booking['end_time'])
            slot_start_dt = datetime.fromisoformat(slot_start)
            slot_end_dt = datetime.fromisoformat(slot_end)
            
            if not (slot_end_dt <= booking_start or slot_start_dt >= booking_end):
                is_available = False
                break
        
        if is_available:
            available_slots.append({
                'start': slot_start,
                'end': slot_end,
                'display': f"{hour:02d}:00 - {hour+1:02d}:00"
            })
    
    return jsonify({'slots': available_slots})

# Routes pour les réservations
@app.route('/book/<int:room_id>', methods=['GET', 'POST'])
@login_required
def book(room_id):
    if request.method == 'POST':
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        
        conn = get_db_connection()
        
        # Vérifier si le créneau est toujours disponible
        existing_booking = conn.execute('''
            SELECT * FROM bookings 
            WHERE room_id = ? AND status = 'confirmed'
            AND ((start_time < ? AND end_time > ?) OR (start_time < ? AND end_time > ?))
        ''', (room_id, end_time, start_time, start_time, end_time)).fetchone()
        
        if existing_booking:
            flash('Ce créneau n\'est plus disponible', 'error')
            conn.close()
            return redirect(url_for('book', room_id=room_id))
        
        # Créer la réservation
        conn.execute('''
            INSERT INTO bookings (user_id, room_id, start_time, end_time, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (current_user.id, room_id, start_time, end_time, 'confirmed', datetime.now()))
        
        conn.commit()
        conn.close()
        
        flash('Réservation confirmée!', 'success')
        return redirect(url_for('my_bookings'))
    
    conn = get_db_connection()
    room = conn.execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()
    conn.close()
    
    if not room:
        flash('Salle non trouvée', 'error')
        return redirect(url_for('rooms'))
    
    return render_template('book.html', room=room)

@app.route('/my_bookings')
@login_required
def my_bookings():
    conn = get_db_connection()
    bookings = conn.execute('''
        SELECT b.*, r.name as room_name, r.capacity, r.price_per_hour
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.user_id = ?
        ORDER BY b.start_time DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/cancel_booking/<int:booking_id>')
@login_required
def cancel_booking(booking_id):
    conn = get_db_connection()
    
    # Vérifier que l'utilisateur est propriétaire de la réservation
    booking = conn.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    
    if not booking:
        flash('Réservation non trouvée', 'error')
        conn.close()
        return redirect(url_for('my_bookings'))
    
    if booking['user_id'] != current_user.id and not current_user.is_admin:
        flash('Vous n\'avez pas la permission d\'annuler cette réservation', 'error')
        conn.close()
        return redirect(url_for('my_bookings'))
    
    # Annuler la réservation
    conn.execute('UPDATE bookings SET status = ? WHERE id = ?', ('cancelled', booking_id))
    conn.commit()
    conn.close()
    
    flash('Réservation annulée avec succès', 'success')
    
    if current_user.is_admin:
        return redirect(url_for('admin_bookings'))
    else:
        return redirect(url_for('my_bookings'))

# Routes administrateur
@app.route('/admin/bookings')
@login_required
def admin_bookings():
    if not current_user.is_admin:
        flash('Accès réservé aux administrateurs', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    bookings = conn.execute('''
        SELECT b.*, u.username, u.email, r.name as room_name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN rooms r ON b.room_id = r.id
        ORDER BY b.start_time DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin_bookings.html', bookings=bookings)

@app.route('/admin/rooms')
@login_required
def admin_rooms():
    if not current_user.is_admin:
        flash('Accès réservé aux administrateurs', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    rooms = conn.execute('SELECT * FROM rooms ORDER BY name').fetchall()
    conn.close()
    
    return render_template('admin_rooms.html', rooms=rooms)

@app.route('/admin/add_room', methods=['GET', 'POST'])
@login_required
def add_room():
    if not current_user.is_admin:
        flash('Accès réservé aux administrateurs', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        capacity = request.form['capacity']
        price_per_hour = request.form['price_per_hour']
        equipment = request.form['equipment']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO rooms (name, description, capacity, price_per_hour, equipment, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (name, description, capacity, price_per_hour, equipment))
        conn.commit()
        conn.close()
        
        flash('Salle ajoutée avec succès!', 'success')
        return redirect(url_for('admin_rooms'))
    
    return render_template('add_room.html')

@app.route('/admin/toggle_room/<int:room_id>')
@login_required
def toggle_room(room_id):
    if not current_user.is_admin:
        flash('Accès réservé aux administrateurs', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    room = conn.execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()
    
    if room:
        new_status = 0 if room['is_active'] else 1
        conn.execute('UPDATE rooms SET is_active = ? WHERE id = ?', (new_status, room_id))
        conn.commit()
        
        status_text = "activée" if new_status else "désactivée"
        flash(f'Salle {status_text} avec succès', 'success')
    
    conn.close()
    return redirect(url_for('admin_rooms'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
```

## 3. Fichier database.py

```python
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
```

## 4. Fichier models.py

```python
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, email, is_admin):
        self.id = id
        self.username = username
        self.email = email
        self.is_admin = bool(is_admin)
    
    def get_id(self):
        return str(self.id)

class Room:
    def __init__(self, id, name, description, capacity, price_per_hour, equipment, is_active):
        self.id = id
        self.name = name
        self.description = description
        self.capacity = capacity
        self.price_per_hour = price_per_hour
        self.equipment = equipment
        self.is_active = is_active

class Booking:
    def __init__(self, id, user_id, room_id, start_time, end_time, status):
        self.id = id
        self.user_id = user_id
        self.room_id = room_id
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
```

## 5. Fichier static/css/style.css

```css
/* Reset et styles de base */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f8f9fa;
}

/* Navbar */
.navbar {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1rem 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.navbar-brand {
    color: white !important;
    font-size: 1.5rem;
    font-weight: bold;
}

.nav-link {
    color: rgba(255,255,255,0.9) !important;
    transition: color 0.3s;
}

.nav-link:hover {
    color: white !important;
}

/* Conteneur principal */
.container {
    max-width: 1200px;
    margin: 2rem auto;
    padding: 0 1rem;
}

/* Cartes */
.card {
    border: none;
    border-radius: 15px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.08);
    transition: transform 0.3s, box-shadow 0.3s;
    margin-bottom: 1.5rem;
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.12);
}

.card-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 15px 15px 0 0 !important;
    padding: 1.25rem;
}

/* Boutons */
.btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 50px;
    font-weight: 600;
    transition: all 0.3s;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.btn-danger {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 50px;
    font-weight: 600;
}

/* Formulaires */
.form-control {
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    transition: border-color 0.3s;
}

.form-control:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
}

/* Alertes */
.alert {
    border-radius: 10px;
    border: none;
    padding: 1rem 1.5rem;
}

/* Tableaux */
.table {
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 5px 15px rgba(0,0,0,0.08);
}

.table th {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    padding: 1rem;
}

.table td {
    padding: 1rem;
    vertical-align: middle;
}

/* Badges */
.badge {
    padding: 0.5rem 1rem;
    border-radius: 50px;
    font-weight: 500;
}

/* Hero section */
.hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 4rem 0;
    border-radius: 20px;
    margin-bottom: 3rem;
    text-align: center;
}

.hero h1 {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.hero p {
    font-size: 1.25rem;
    opacity: 0.9;
}

/* Cards de salles */
.room-card {
    height: 100%;
}

.room-card .card-body {
    display: flex;
    flex-direction: column;
}

.room-features {
    list-style: none;
    padding-left: 0;
    margin-top: 1rem;
}

.room-features li {
    padding: 0.25rem 0;
    color: #666;
}

.room-features li:before {
    content: "✓";
    color: #667eea;
    font-weight: bold;
    margin-right: 0.5rem;
}

/* Créneaux horaires */
.time-slots {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.75rem;
    margin-top: 1rem;
}

.time-slot {
    padding: 0.75rem;
    background: #f8f9fa;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s;
}

.time-slot:hover {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

.time-slot.selected {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

/* Responsive */
@media (max-width: 768px) {
    .hero h1 {
        font-size: 2rem;
    }
    
    .table-responsive {
        font-size: 0.9rem;
    }
    
    .time-slots {
        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    }
}
```

## 6. Fichier static/js/script.js

```javascript
// Gestion des créneaux horaires
document.addEventListener('DOMContentLoaded', function() {
    // Sélection de date pour la réservation
    const dateInput = document.getElementById('date');
    const roomIdInput = document.getElementById('room_id');
    const timeSlotsContainer = document.getElementById('time-slots');
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    
    if (dateInput && roomIdInput && timeSlotsContainer) {
        dateInput.addEventListener('change', loadAvailableSlots);
        
        function loadAvailableSlots() {
            const date = dateInput.value;
            const roomId = roomIdInput.value;
            
            if (!date || !roomId) return;
            
            fetch(`/api/available_slots?room_id=${roomId}&date=${date}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        timeSlotsContainer.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                        return;
                    }
                    
                    if (data.slots.length === 0) {
                        timeSlotsContainer.innerHTML = '<div class="alert alert-warning">Aucun créneau disponible pour cette date</div>';
                        return;
                    }
                    
                    let html = '<div class="time-slots">';
                    data.slots.forEach(slot => {
                        html += `
                            <div class="time-slot" data-start="${slot.start}" data-end="${slot.end}">
                                ${slot.display}
                            </div>
                        `;
                    });
                    html += '</div>';
                    
                    timeSlotsContainer.innerHTML = html;
                    
                    // Ajouter les événements de clic sur les créneaux
                    document.querySelectorAll('.time-slot').forEach(slot => {
                        slot.addEventListener('click', function() {
                            // Désélectionner tous les créneaux
                            document.querySelectorAll('.time-slot').forEach(s => {
                                s.classList.remove('selected');
                            });
                            
                            // Sélectionner le créneau cliqué
                            this.classList.add('selected');
                            
                            // Remplir les champs cachés
                            startTimeInput.value = this.dataset.start;
                            endTimeInput.value = this.dataset.end;
                        });
                    });
                })
                .catch(error => {
                    console.error('Erreur:', error);
                    timeSlotsContainer.innerHTML = '<div class="alert alert-danger">Erreur de chargement des créneaux</div>';
                });
        }
        
        // Charger les créneaux si une date est déjà sélectionnée
        if (dateInput.value) {
            loadAvailableSlots();
        }
    }
    
    // Confirmation de suppression
    const cancelButtons = document.querySelectorAll('.cancel-booking');
    cancelButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Êtes-vous sûr de vouloir annuler cette réservation ?')) {
                e.preventDefault();
            }
        });
    });
    
    // Confirmation de désactivation de salle
    const toggleRoomButtons = document.querySelectorAll('.toggle-room');
    toggleRoomButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const action = this.dataset.action;
            if (!confirm(`Êtes-vous sûr de vouloir ${action} cette salle ?`)) {
                e.preventDefault();
            }
        });
    });
    
    // Formatage des dates
    const dateElements = document.querySelectorAll('.format-date');
    dateElements.forEach(element => {
        const date = new Date(element.textContent);
        element.textContent = date.toLocaleDateString('fr-FR', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    });
});
```

## 7. Templates HTML

### base.html
```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Coworking Space - Réservation de salles{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="fas fa-building me-2"></i>Coworking Space
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}"><i class="fas fa-home me-1"></i>Accueil</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('rooms') }}"><i class="fas fa-door-open me-1"></i>Salles</a>
                    </li>
                    {% if current_user.is_authenticated %}
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('my_bookings') }}"><i class="fas fa-calendar-alt me-1"></i>Mes réservations</a>
                        </li>
                        {% if current_user.is_admin %}
                            <li class="nav-item dropdown">
                                <a class="nav-link dropdown-toggle" href="#" id="adminDropdown" role="button" data-bs-toggle="dropdown">
                                    <i class="fas fa-user-shield me-1"></i>Admin
                                </a>
                                <ul class="dropdown-menu">
                                    <li><a class="dropdown-item" href="{{ url_for('admin_bookings') }}">Toutes les réservations</a></li>
                                    <li><a class="dropdown-item" href="{{ url_for('admin_rooms') }}">Gérer les salles</a></li>
                                    <li><a class="dropdown-item" href="{{ url_for('add_room') }}">Ajouter une salle</a></li>
                                </ul>
                            </li>
                        {% endif %}
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('logout') }}"><i class="fas fa-sign-out-alt me-1"></i>Déconnexion</a>
                        </li>
                        <li class="nav-item">
                            <span class="nav-link disabled">Bonjour, {{ current_user.username }}</span>
                        </li>
                    {% else %}
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('login') }}"><i class="fas fa-sign-in-alt me-1"></i>Connexion</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('register') }}"><i class="fas fa-user-plus me-1"></i>Inscription</a>
                        </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' if category == 'success' else 'info' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <footer class="mt-5 py-4 bg-light">
        <div class="container text-center">
            <p class="mb-0">&copy; 2024 Coworking Space. Tous droits réservés.</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### index.html
```html
{% extends "base.html" %}

{% block title %}Accueil - Coworking Space{% endblock %}

{% block content %}
<div class="hero">
    <h1>Bienvenue au Coworking Space</h1>
    <p class="lead">Réservez facilement vos salles de réunion et espaces de travail</p>
    {% if not current_user.is_authenticated %}
        <div class="mt-4">
            <a href="{{ url_for('register') }}" class="btn btn-light btn-lg me-3">Créer un compte</a>
            <a href="{{ url_for('rooms') }}" class="btn btn-outline-light btn-lg">Voir les salles</a>
        </div>
    {% else %}
        <div class="mt-4">
            <a href="{{ url_for('rooms') }}" class="btn btn-light btn-lg me-3">Réserver une salle</a>
            <a href="{{ url_for('my_bookings') }}" class="btn btn-outline-light btn-lg">Mes réservations</a>
        </div>
    {% endif %}
</div>

<div class="row mt-5">
    <div class="col-md-4 mb-4">
        <div class="card h-100 text-center">
            <div class="card-body">
                <i class="fas fa-search fa-3x text-primary mb-3"></i>
                <h3 class="card-title">Trouvez</h3>
                <p class="card-text">Parcourez nos salles disponibles et choisissez celle qui correspond à vos besoins.</p>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-4">
        <div class="card h-100 text-center">
            <div class="card-body">
                <i class="fas fa-calendar-check fa-3x text-primary mb-3"></i>
                <h3 class="card-title">Réservez</h3>
                <p class="card-text">Sélectionnez la date et l'heure qui vous conviennent en quelques clics.</p>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-4">
        <div class="card h-100 text-center">
            <div class="card-body">
                <i class="fas fa-users fa-3x text-primary mb-3"></i>
                <h3 class="card-title">Collaborez</h3>
                <p class="card-text">Travaillez efficacement dans des espaces conçus pour la productivité.</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### login.html
```html
{% extends "base.html" %}

{% block title %}Connexion - Coworking Space{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="text-center mb-0"><i class="fas fa-sign-in-alt me-2"></i>Connexion</h3>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('login') }}">
                    <div class="mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email" class="form-control" id="email" name="email" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Mot de passe</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">Se connecter</button>
                    </div>
                </form>
                <div class="text-center mt-3">
                    <p>Pas encore de compte ? <a href="{{ url_for('register') }}">S'inscrire</a></p>
                </div>
                <div class="text-center mt-2">
                    <small class="text-muted">Compte administrateur test : admin@coworking.com / admin123</small>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### register.html
```html
{% extends "base.html" %}

{% block title %}Inscription - Coworking Space{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="text-center mb-0"><i class="fas fa-user-plus me-2"></i>Créer un compte</h3>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('register') }}">
                    <div class="mb-3">
                        <label for="username" class="form-label">Nom d'utilisateur</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email" class="form-control" id="email" name="email" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Mot de passe</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">S'inscrire</button>
                    </div>
                </form>
                <div class="text-center mt-3">
                    <p>Déjà un compte ? <a href="{{ url_for('login') }}">Se connecter</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### rooms.html
```html
{% extends "base.html" %}

{% block title %}Nos salles - Coworking Space{% endblock %}

{% block content %}
<h1 class="mb-4"><i class="fas fa-door-open me-2"></i>Nos salles de coworking</h1>

<div class="row">
    {% for room in rooms %}
    <div class="col-md-4 mb-4">
        <div class="card room-card">
            <div class="card-header">
                <h5 class="mb-0">{{ room.name }}</h5>
            </div>
            <div class="card-body">
                <p class="card-text">{{ room.description }}</p>
                <ul class="room-features">
                    <li>Capacité : {{ room.capacity }} personnes</li>
                    <li>Prix : {{ room.price_per_hour }}€/heure</li>
                    {% if room.equipment %}
                        <li>Équipement : {{ room.equipment }}</li>
                    {% endif %}
                </ul>
            </div>
            <div class="card-footer bg-transparent">
                {% if current_user.is_authenticated %}
                    <a href="{{ url_for('book', room_id=room.id) }}" class="btn btn-primary w-100">
                        <i class="fas fa-calendar-plus me-2"></i>Réserver
                    </a>
                {% else %}
                    <a href="{{ url_for('login') }}" class="btn btn-outline-primary w-100">
                        <i class="fas fa-sign-in-alt me-2"></i>Connectez-vous pour réserver
                    </a>
                {% endif %}
            </div>
        </div>
    </div>
    {% endfor %}
</div>
{% endblock %}
```

### book.html
```html
{% extends "base.html" %}

{% block title %}Réserver {{ room.name }} - Coworking Space{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h3 class="mb-0"><i class="fas fa-calendar-plus me-2"></i>Réserver : {{ room.name }}</h3>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <div class="card mb-3">
                            <div class="card-body">
                                <h5>Détails de la salle</h5>
                                <p><strong>Capacité :</strong> {{ room.capacity }} personnes</p>
                                <p><strong>Prix :</strong> {{ room.price_per_hour }}€/heure</p>
                                <p><strong>Équipement :</strong> {{ room.equipment }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <form method="POST" action="{{ url_for('book', room_id=room.id) }}">
                            <input type="hidden" id="room_id" value="{{ room.id }}">
                            
                            <div class="mb-3">
                                <label for="date" class="form-label">Sélectionnez une date</label>
                                <input type="date" class="form-control" id="date" name="date" 
                                       min="{{ today }}" required>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Créneaux disponibles</label>
                                <div id="time-slots" class="mb-3">
                                    <p class="text-muted">Sélectionnez d'abord une date</p>
                                </div>
                            </div>
                            
                            <input type="hidden" id="start_time" name="start_time" required>
                            <input type="hidden" id="end_time" name="end_time" required>
                            
                            <div class="d-grid">
                                <button type="submit" class="btn btn-primary" id="submit-btn" disabled>
                                    Confirmer la réservation
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    // Définir la date d'aujourd'hui comme minimum
    document.addEventListener('DOMContentLoaded', function() {
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('date').min = today;
        
        // Activer/désactiver le bouton de soumission
        const startTimeInput = document.getElementById('start_time');
        const submitBtn = document.getElementById('submit-btn');
        
        startTimeInput.addEventListener('change', function() {
            submitBtn.disabled = !this.value;
        });
    });
</script>
{% endblock %}
```

### my_bookings.html
```html
{% extends "base.html" %}

{% block title %}Mes réservations - Coworking Space{% endblock %}

{% block content %}
<h1 class="mb-4"><i class="fas fa-calendar-alt me-2"></i>Mes réservations</h1>

<div class="card">
    <div class="card-header">
        <h5 class="mb-0">Réservations futures et passées</h5>
    </div>
    <div class="card-body">
        {% if bookings %}
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Salle</th>
                        <th>Date et heure</th>
                        <th>Durée</th>
                        <th>Prix total</th>
                        <th>Statut</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for booking in bookings %}
                    <tr>
                        <td>{{ booking.room_name }}</td>
                        <td class="format-date">{{ booking.start_time }}</td>
                        <td>
                            {% set duration = ((booking.end_time|string|to_datetime) - (booking.start_time|string|to_datetime)).seconds // 3600 %}
                            {{ duration }} heure{% if duration > 1 %}s{% endif %}
                        </td>
                        <td>{{ booking.price_per_hour * duration }}€</td>
                        <td>
                            {% if booking.status == 'confirmed' %}
                                <span class="badge bg-success">Confirmée</span>
                            {% elif booking.status == 'cancelled' %}
                                <span class="badge bg-danger">Annulée</span>
                            {% else %}
                                <span class="badge bg-warning">{{ booking.status }}</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if booking.status == 'confirmed' and booking.start_time|string|to_datetime > now %}
                                <a href="{{ url_for('cancel_booking', booking_id=booking.id) }}" 
                                   class="btn btn-sm btn-danger cancel-booking">
                                    <i class="fas fa-times me-1"></i>Annuler
                                </a>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <div class="text-center py-4">
            <i class="fas fa-calendar-times fa-3x text-muted mb-3"></i>
            <p class="text-muted">Vous n'avez aucune réservation pour le moment.</p>
            <a href="{{ url_for('rooms') }}" class="btn btn-primary">Réserver une salle</a>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}
```

### admin_bookings.html
```html
{% extends "base.html" %}

{% block title %}Gestion des réservations - Coworking Space{% endblock %}

{% block content %}
<h1 class="mb-4"><i class="fas fa-user-shield me-2"></i>Gestion des réservations</h1>

<div class="card">
    <div class="card-header">
        <h5 class="mb-0">Toutes les réservations</h5>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Utilisateur</th>
                        <th>Salle</th>
                        <th>Date et heure</th>
                        <th>Durée</th>
                        <th>Statut</th>
                        <th>Créée le</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for booking in bookings %}
                    <tr>
                        <td>{{ booking.id }}</td>
                        <td>{{ booking.username }}<br><small>{{ booking.email }}</small></td>
                        <td>{{ booking.room_name }}</td>
                        <td class="format-date">{{ booking.start_time }}</td>
                        <td>
                            {% set duration = ((booking.end_time|string|to_datetime) - (booking.start_time|string|to_datetime)).seconds // 3600 %}
                            {{ duration }}h
                        </td>
                        <td>
                            {% if booking.status == 'confirmed' %}
                                <span class="badge bg-success">Confirmée</span>
                            {% elif booking.status == 'cancelled' %}
                                <span class="badge bg-danger">Annulée</span>
                            {% else %}
                                <span class="badge bg-warning">{{ booking.status }}</span>
                            {% endif %}
                        </td>
                        <td class="format-date">{{ booking.created_at }}</td>
                        <td>
                            {% if booking.status == 'confirmed' and booking.start_time|string|to_datetime > now %}
                                <a href="{{ url_for('cancel_booking', booking_id=booking.id) }}" 
                                   class="btn btn-sm btn-danger cancel-booking">
                                    <i class="fas fa-times me-1"></i>Annuler
                                </a>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
```

### admin_rooms.html
```html
{% extends "base.html" %}

{% block title %}Gestion des salles - Coworking Space{% endblock %}

{% block content %}
<h1 class="mb-4"><i class="fas fa-user-shield me-2"></i>Gestion des salles</h1>

<div class="mb-4">
    <a href="{{ url_for('add_room') }}" class="btn btn-primary">
        <i class="fas fa-plus me-2"></i>Ajouter une salle
    </a>
</div>

<div class="card">
    <div class="card-header">
        <h5 class="mb-0">Liste des salles</h5>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Nom</th>
                        <th>Description</th>
                        <th>Capacité</th>
                        <th>Prix/heure</th>
                        <th>Équipement</th>
                        <th>Statut</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for room in rooms %}
                    <tr>
                        <td>{{ room.id }}</td>
                        <td>{{ room.name }}</td>
                        <td>{{ room.description }}</td>
                        <td>{{ room.capacity }}</td>
                        <td>{{ room.price_per_hour }}€</td>
                        <td>{{ room.equipment }}</td>
                        <td>
                            {% if room.is_active %}
                                <span class="badge bg-success">Active</span>
                            {% else %}
                                <span class="badge bg-danger">Inactive</span>
                            {% endif %}
                        </td>
                        <td>
                            <a href="{{ url_for('toggle_room', room_id=room.id) }}" 
                               class="btn btn-sm {% if room.is_active %}btn-warning{% else %}btn-success{% endif %} toggle-room"
                               data-action="{% if room.is_active %}désactiver{% else %}activer{% endif %}">
                                <i class="fas {% if room.is_active %}fa-ban{% else %}fa-check{% endif %} me-1"></i>
                                {% if room.is_active %}Désactiver{% else %}Activer{% endif %}
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
```

### add_room.html
```html
{% extends "base.html" %}

{% block title %}Ajouter une salle - Coworking Space{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h3 class="mb-0"><i class="fas fa-plus me-2"></i>Ajouter une nouvelle salle</h3>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('add_room') }}">
                    <div class="mb-3">
                        <label for="name" class="form-label">Nom de la salle</label>
                        <input type="text" class="form-control" id="name" name="name" required>
                    </div>
                    
                    <div class="mb-3">
                        <label for="description" class="form-label">Description</label>
                        <textarea class="form-control" id="description" name="description" rows="3" required></textarea>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="capacity" class="form-label">Capacité (personnes)</label>
                            <input type="number" class="form-control" id="capacity" name="capacity" min="1" required>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <label for="price_per_hour" class="form-label">Prix par heure (€)</label>
                            <input type="number" class="form-control" id="price_per_hour" name="price_per_hour" 
                                   min="0" step="0.01" required>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="equipment" class="form-label">Équipement</label>
                        <textarea class="form-control" id="equipment" name="equipment" rows="2"></textarea>
                        <div class="form-text">Listez les équipements disponibles, séparés par des virgules</div>
                    </div>
                    
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">Ajouter la salle</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## Instructions d'installation et d'utilisation

### 1. Installation

```bash
# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Sur Windows :
venv\Scripts\activate
# Sur Mac/Linux :
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configuration

```python
# Dans app.py, modifiez la clé secrète
app.config['SECRET_KEY'] = 'votre_cle_secrete_ici_plus_longue_et_aleatoire'
```

### 3. Lancement de l'application

```bash
python app.py
```

L'application sera accessible à l'adresse : `http://localhost:5000`

### 4. Comptes par défaut

- **Administrateur** : 
  - Email : `admin@coworking.com`
  - Mot de passe : `admin123`

- **Utilisateurs** : 
  - Créez votre propre compte via le formulaire d'inscription

## Fonctionnalités implémentées

### Pour les clients :
1. **Inscription/Connexion** avec système d'authentification
2. **Visualisation des salles** disponibles avec leurs caractéristiques
3. **Réservation de salles** avec sélection de date et heure
4. **Gestion des réservations** personnelles (visualisation, annulation)
5. **Interface responsive** et moderne

### Pour les administrateurs :
1. **Tableau de bord** avec toutes les réservations
2. **Gestion des salles** (ajout, activation/désactivation)
3. **Annulation de réservations** pour tous les utilisateurs
4. **Statistiques** sur l'utilisation des salles

### Fonctionnalités techniques :
1. **Base de données SQLite** avec relations entre tables
2. **API REST** pour les créneaux disponibles
3. **Validation des données** côté serveur
4. **Messages flash** pour le feedback utilisateur
5. **Sécurité** avec protection CSRF et authentification
6. **Interface responsive** avec Bootstrap 5

## Améliorations possibles

1. **Paiement en ligne** avec Stripe ou PayPal
2. **Notifications par email** pour les confirmations de réservation
3. **Système de notation** des salles
4. **Calendrier intégré** pour visualiser les disponibilités
5. **Recherche avancée** avec filtres
6. **Export des réservations** en PDF ou Excel
7. **Système de parrainage** pour les utilisateurs
8. **API complète** pour intégration mobile

Cette application est prête à être utilisée et peut être déployée sur un serveur comme Heroku, PythonAnywhere ou un VPS traditionnel.