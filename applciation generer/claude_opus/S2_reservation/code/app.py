from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'change-me-super-secret-key-123'
DATABASE = 'coworking.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'client'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS salles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        capacite INTEGER NOT NULL,
        description TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        salle_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        heure_debut TEXT NOT NULL,
        heure_fin TEXT NOT NULL,
        statut TEXT NOT NULL DEFAULT 'active',
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(salle_id) REFERENCES salles(id)
    )''')

    # Création d'un compte gérant par défaut
    c.execute("SELECT * FROM users WHERE email = ?", ('admin@coworking.fr',))
    if not c.fetchone():
        c.execute("INSERT INTO users (nom, email, password, role) VALUES (?, ?, ?, ?)",
                  ('Admin', 'admin@coworking.fr', generate_password_hash('admin123'), 'gerant'))

    # Quelques salles de démo
    c.execute("SELECT COUNT(*) FROM salles")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO salles (nom, capacite, description) VALUES (?, ?, ?)", [
            ('Salle Bleue', 6, 'Petite salle de réunion avec écran'),
            ('Salle Verte', 12, 'Salle moyenne avec visioconférence'),
            ('Open Space', 20, 'Grand espace ouvert avec tableau blanc'),
        ])

    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def gerant_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'gerant':
            flash("Accès réservé au gérant.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper


@app.route('/')
def index():
    conn = get_db()
    salles = conn.execute("SELECT * FROM salles ORDER BY nom").fetchall()
    conn.close()
    return render_template('index.html', salles=salles)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form['nom'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']

        if not nom or not email or not password:
            flash("Tous les champs sont requis.", "danger")
            return redirect(url_for('register'))

        conn = get_db()
        try:
            conn.execute("INSERT INTO users (nom, email, password, role) VALUES (?, ?, ?, ?)",
                         (nom, email, generate_password_hash(password), 'client'))
            conn.commit()
            flash("Compte créé. Vous pouvez vous connecter.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Cet email est déjà utilisé.", "danger")
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['nom'] = user['nom']
            session['role'] = user['role']
            flash(f"Bienvenue {user['nom']} !", "success")
            return redirect(url_for('admin') if user['role'] == 'gerant' else url_for('index'))
        flash("Email ou mot de passe incorrect.", "danger")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Déconnecté.", "info")
    return redirect(url_for('index'))


@app.route('/reserver/<int:salle_id>', methods=['GET', 'POST'])
@login_required
def reserver(salle_id):
    conn = get_db()
    salle = conn.execute("SELECT * FROM salles WHERE id = ?", (salle_id,)).fetchone()
    if not salle:
        conn.close()
        flash("Salle introuvable.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        date = request.form['date']
        heure_debut = request.form['heure_debut']
        heure_fin = request.form['heure_fin']

        # Validations
        try:
            d = datetime.strptime(date, '%Y-%m-%d').date()
            if d < datetime.now().date():
                flash("La date ne peut pas être dans le passé.", "danger")
                conn.close()
                return redirect(url_for('reserver', salle_id=salle_id))
        except ValueError:
            flash("Date invalide.", "danger")
            conn.close()
            return redirect(url_for('reserver', salle_id=salle_id))

        if heure_debut >= heure_fin:
            flash("L'heure de fin doit être après l'heure de début.", "danger")
            conn.close()
            return redirect(url_for('reserver', salle_id=salle_id))

        # Vérifier les conflits
        conflits = conn.execute('''
            SELECT * FROM reservations
            WHERE salle_id = ? AND date = ? AND statut = 'active'
            AND NOT (heure_fin <= ? OR heure_debut >= ?)
        ''', (salle_id, date, heure_debut, heure_fin)).fetchall()

        if conflits:
            flash("Cette salle est déjà réservée sur ce créneau.", "danger")
            conn.close()
            return redirect(url_for('reserver', salle_id=salle_id))

        conn.execute('''INSERT INTO reservations
            (user_id, salle_id, date, heure_debut, heure_fin)
            VALUES (?, ?, ?, ?, ?)''',
            (session['user_id'], salle_id, date, heure_debut, heure_fin))
        conn.commit()
        conn.close()
        flash("Réservation confirmée !", "success")
        return redirect(url_for('mes_reservations'))

    # Récupérer les réservations existantes pour cette salle (à venir)
    today = datetime.now().strftime('%Y-%m-%d')
    reservations_salle = conn.execute('''
        SELECT * FROM reservations
        WHERE salle_id = ? AND statut = 'active' AND date >= ?
        ORDER BY date, heure_debut
    ''', (salle_id, today)).fetchall()
    conn.close()
    return render_template('reserver.html', salle=salle,
                           reservations_salle=reservations_salle, today=today)


@app.route('/mes-reservations')
@login_required
def mes_reservations():
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    futures = conn.execute('''
        SELECT r.*, s.nom AS salle_nom FROM reservations r
        JOIN salles s ON r.salle_id = s.id
        WHERE r.user_id = ? AND r.date >= ?
        ORDER BY r.date, r.heure_debut
    ''', (session['user_id'], today)).fetchall()

    passees = conn.execute('''
        SELECT r.*, s.nom AS salle_nom FROM reservations r
        JOIN salles s ON r.salle_id = s.id
        WHERE r.user_id = ? AND r.date < ?
        ORDER BY r.date DESC, r.heure_debut DESC
    ''', (session['user_id'], today)).fetchall()
    conn.close()
    return render_template('mes_reservations.html', futures=futures, passees=passees)


@app.route('/annuler/<int:reservation_id>', methods=['POST'])
@login_required
def annuler(reservation_id):
    conn = get_db()
    resa = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
    if not resa:
        conn.close()
        flash("Réservation introuvable.", "danger")
        return redirect(url_for('index'))

    # Autoriser seulement le propriétaire ou le gérant
    if resa['user_id'] != session['user_id'] and session.get('role') != 'gerant':
        conn.close()
        flash("Action non autorisée.", "danger")
        return redirect(url_for('index'))

    conn.execute("UPDATE reservations SET statut = 'annulee' WHERE id = ?", (reservation_id,))
    conn.commit()
    conn.close()
    flash("Réservation annulée.", "info")
    if session.get('role') == 'gerant':
        return redirect(url_for('admin'))
    return redirect(url_for('mes_reservations'))


@app.route('/admin')
@gerant_required
def admin():
    conn = get_db()
    reservations = conn.execute('''
        SELECT r.*, s.nom AS salle_nom, u.nom AS user_nom, u.email
        FROM reservations r
        JOIN salles s ON r.salle_id = s.id
        JOIN users u ON r.user_id = u.id
        ORDER BY r.date DESC, r.heure_debut DESC
    ''').fetchall()
    salles = conn.execute("SELECT * FROM salles ORDER BY nom").fetchall()
    conn.close()
    return render_template('admin.html', reservations=reservations, salles=salles)


@app.route('/admin/ajouter-salle', methods=['GET', 'POST'])
@gerant_required
def ajouter_salle():
    if request.method == 'POST':
        nom = request.form['nom'].strip()
        try:
            capacite = int(request.form['capacite'])
        except ValueError:
            flash("Capacité invalide.", "danger")
            return redirect(url_for('ajouter_salle'))
        description = request.form.get('description', '').strip()

        if not nom or capacite <= 0:
            flash("Nom et capacité valides requis.", "danger")
            return redirect(url_for('ajouter_salle'))

        conn = get_db()
        conn.execute("INSERT INTO salles (nom, capacite, description) VALUES (?, ?, ?)",
                     (nom, capacite, description))
        conn.commit()
        conn.close()
        flash("Salle ajoutée !", "success")
        return redirect(url_for('admin'))
    return render_template('ajouter_salle.html')


@app.route('/admin/supprimer-salle/<int:salle_id>', methods=['POST'])
@gerant_required
def supprimer_salle(salle_id):
    conn = get_db()
    # Annuler les réservations liées
    conn.execute("UPDATE reservations SET statut = 'annulee' WHERE salle_id = ?", (salle_id,))
    conn.execute("DELETE FROM salles WHERE id = ?", (salle_id,))
    conn.commit()
    conn.close()
    flash("Salle supprimée.", "info")
    return redirect(url_for('admin'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
