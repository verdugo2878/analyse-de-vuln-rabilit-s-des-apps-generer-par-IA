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
