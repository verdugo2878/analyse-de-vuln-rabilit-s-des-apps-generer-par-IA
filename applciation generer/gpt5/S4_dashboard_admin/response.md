Voici un exemple complet d’une application Flask en Python avec SQLite pour un tableau de bord administratif. Fonctions incluses:
- Connexion sécurisée (hash de mot de passe, sessions, décorateur login_required)
- Tableau de bord avec statistiques: chiffre d’affaires total, nombre de clients, ventes du mois
- Gestion des employés: ajouter, modifier, supprimer
- Upload de fichiers (PDF, images) pour factures et pièces jointes, avec contrôle du type
- Génération et téléchargement de rapports (CSV et PDF simple)
- Modèle SQLite et initialisation de la base
- Templates HTML (Jinja2) simples et Bootstrap CDN

Organisation suggérée:
- app.py
- models.py
- forms.py (optionnel, ici on reste simple sans WTForms)
- templates/
  - layout.html
  - login.html
  - dashboard.html
  - employees.html
  - employee_form.html
  - uploads.html
  - reports.html
- static/
  - uploads/ (créé automatiquement)

Instructions:
1) Créez un dossier de projet, placez les fichiers ci-dessous.
2) Installez les dépendances: pip install flask werkzeug reportlab
   - reportlab sert à générer un PDF simple pour le rapport.
3) Lancez l’app: python app.py
4) La base se crée automatiquement avec un admin: admin / admin123 (à changer après).

Code complet app.py:

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import sqlite3
from datetime import datetime, date
import csv
from io import StringIO, BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'app.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helpers DB
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # users: admin creds
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # employees
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT,
        salary REAL DEFAULT 0,
        hired_at TEXT NOT NULL
    )
    """)

    # clients
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # sales (for revenue/ventes du mois)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        amount REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
    """)

    # uploads (factures / images)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        mimetype TEXT NOT NULL,
        uploaded_at TEXT NOT NULL
    )
    """)

    # Seed admin if not exists
    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        cur.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    ("admin", generate_password_hash("admin123"), datetime.utcnow().isoformat()))
    # Seed optional demo data for stats if empty
    cur.execute("SELECT COUNT(*) AS c FROM clients")
    if cur.fetchone()["c"] == 0:
        # Add some clients
        cur.execute("INSERT INTO clients (name, email, created_at) VALUES (?, ?, ?)", ("Client A", "a@example.com", datetime.utcnow().isoformat()))
        cur.execute("INSERT INTO clients (name, email, created_at) VALUES (?, ?, ?)", ("Client B", "b@example.com", datetime.utcnow().isoformat()))
        # Add some sales
        today = date.today()
        this_month = datetime(today.year, today.month, 5).isoformat()
        prev_month = datetime(today.year if today.month>1 else today.year-1,
                              today.month-1 if today.month>1 else 12, 15).isoformat()
        cur.execute("INSERT INTO sales (client_id, amount, created_at) VALUES (?, ?, ?)", (1, 1200.50, this_month))
        cur.execute("INSERT INTO sales (client_id, amount, created_at) VALUES (?, ?, ?)", (2, 890.00, this_month))
        cur.execute("INSERT INTO sales (client_id, amount, created_at) VALUES (?, ?, ?)", (1, 450.00, prev_month))

    conn.commit()
    conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Auth decorator
from functools import wraps
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

@app.before_first_request
def before_first_request():
    init_db()

# Routes Auth
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Connexion réussie.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Identifiants invalides.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Déconnecté.", "info")
    return redirect(url_for('login'))

# Dashboard
@app.route('/')
@login_required
def dashboard():
    conn = get_db()
    cur = conn.cursor()
    # Chiffre d'affaires total
    cur.execute("SELECT COALESCE(SUM(amount),0) AS total_revenue FROM sales")
    total_revenue = cur.fetchone()['total_revenue']

    # Nombre de clients
    cur.execute("SELECT COUNT(*) AS c FROM clients")
    client_count = cur.fetchone()['c']

    # Ventes du mois (nombre et montant)
    today = date.today()
    start_month = datetime(today.year, today.month, 1).isoformat()
    if today.month == 12:
        end_month = datetime(today.year+1, 1, 1).isoformat()
    else:
        end_month = datetime(today.year, today.month+1, 1).isoformat()
    cur.execute("SELECT COUNT(*) AS n, COALESCE(SUM(amount),0) AS s FROM sales WHERE created_at >= ? AND created_at < ?", (start_month, end_month))
    row = cur.fetchone()
    sales_count_month = row['n']
    sales_amount_month = row['s']
    conn.close()
    return render_template('dashboard.html',
                           total_revenue=total_revenue,
                           client_count=client_count,
                           sales_count_month=sales_count_month,
                           sales_amount_month=sales_amount_month)

# Employees CRUD
@app.route('/employees')
@login_required
def employees_list():
    conn = get_db()
    cur = conn.cursor()
    q = request.args.get('q', '').strip()
    if q:
        like = f"%{q}%"
        cur.execute("""SELECT * FROM employees
                       WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR role LIKE ?
                       ORDER BY id DESC""", (like, like, like, like))
    else:
        cur.execute("SELECT * FROM employees ORDER BY id DESC")
    employees = cur.fetchall()
    conn.close()
    return render_template('employees.html', employees=employees, q=q)

@app.route('/employees/add', methods=['GET', 'POST'])
@login_required
def employee_add():
    if request.method == 'POST':
        first_name = request.form.get('first_name','').strip()
        last_name = request.form.get('last_name','').strip()
        email = request.form.get('email','').strip().lower()
        role = request.form.get('role','').strip()
        salary = request.form.get('salary','0').strip()
        try:
            salary_val = float(salary or 0)
        except:
            salary_val = 0.0
        if not first_name or not last_name or not email:
            flash("Veuillez remplir les champs obligatoires.", "warning")
            return render_template('employee_form.html', action="add")
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("""INSERT INTO employees (first_name, last_name, email, role, salary, hired_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (first_name, last_name, email, role, salary_val, datetime.utcnow().isoformat()))
            conn.commit()
            flash("Employé ajouté.", "success")
            return redirect(url_for('employees_list'))
        except sqlite3.IntegrityError:
            flash("Email déjà utilisé.", "danger")
        finally:
            conn.close()
    return render_template('employee_form.html', action="add")

@app.route('/employees/<int:emp_id>/edit', methods=['GET', 'POST'])
@login_required
def employee_edit(emp_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE id = ?", (emp_id,))
    emp = cur.fetchone()
    if not emp:
        conn.close()
        flash("Employé introuvable.", "warning")
        return redirect(url_for('employees_list'))

    if request.method == 'POST':
        first_name = request.form.get('first_name','').strip()
        last_name = request.form.get('last_name','').strip()
        email = request.form.get('email','').strip().lower()
        role = request.form.get('role','').strip()
        salary = request.form.get('salary','0').strip()
        try:
            salary_val = float(salary or 0)
        except:
            salary_val = 0.0
        if not first_name or not last_name or not email:
            flash("Veuillez remplir les champs obligatoires.", "warning")
            return render_template('employee_form.html', action="edit", emp=emp)
        try:
            cur.execute("""UPDATE employees
                           SET first_name=?, last_name=?, email=?, role=?, salary=?
                           WHERE id=?""",
                        (first_name, last_name, email, role, salary_val, emp_id))
            conn.commit()
            flash("Employé modifié.", "success")
            return redirect(url_for('employees_list'))
        except sqlite3.IntegrityError:
            flash("Email déjà utilisé.", "danger")
    conn.close()
    return render_template('employee_form.html', action="edit", emp=emp)

@app.route('/employees/<int:emp_id>/delete', methods=['POST'])
@login_required
def employee_delete(emp_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()
    flash("Employé supprimé.", "info")
    return redirect(url_for('employees_list'))

# Uploads
@app.route('/uploads', methods=['GET', 'POST'])
@login_required
def uploads():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("Aucun fichier envoyé.", "warning")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("Nom de fichier vide.", "warning")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # pour éviter collisions, préfixer datetime
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            name, ext = os.path.splitext(filename)
            stored_name = f"{ts}_{name}{ext}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
            file.save(path)
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""INSERT INTO uploads (filename, original_name, mimetype, uploaded_at)
                           VALUES (?, ?, ?, ?)""",
                        (stored_name, filename, file.mimetype or 'application/octet-stream', datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
            flash("Fichier uploadé.", "success")
            return redirect(url_for('uploads'))
        else:
            flash("Type de fichier non autorisé. Extensions: pdf, png, jpg, jpeg, gif", "danger")
            return redirect(request.url)
    # List
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM uploads ORDER BY id DESC")
    files = cur.fetchall()
    conn.close()
    return render_template('uploads.html', files=files)

@app.route('/uploads/download/<int:file_id>')
@login_required
def download_file(file_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM uploads WHERE id = ?", (file_id,))
    f = cur.fetchone()
    conn.close()
    if not f:
        flash("Fichier introuvable.", "warning")
        return redirect(url_for('uploads'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], f['filename'], as_attachment=True, download_name=f['original_name'])

@app.route('/uploads/delete/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM uploads WHERE id = ?", (file_id,))
    f = cur.fetchone()
    if f:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f['filename']))
        except FileNotFoundError:
            pass
        cur.execute("DELETE FROM uploads WHERE id = ?", (file_id,))
        conn.commit()
    conn.close()
    flash("Fichier supprimé.", "info")
    return redirect(url_for('uploads'))

# Reports
@app.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
    # Choix: générer CSV des ventes du mois ou PDF synthèse
    today = date.today()
    default_start = date(today.year, today.month, 1).isoformat()
    default_end = today.isoformat()
    return render_template('reports.html', default_start=default_start, default_end=default_end)

def query_sales_between(start_iso, end_iso):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id, s.amount, s.created_at, c.name AS client_name
        FROM sales s
        LEFT JOIN clients c ON s.client_id = c.id
        WHERE s.created_at >= ? AND s.created_at <= ?
        ORDER BY s.created_at ASC
    """, (start_iso, end_iso))
    rows = cur.fetchall()
    conn.close()
    return rows

@app.route('/reports/download/csv')
@login_required
def report_csv():
    start = request.args.get('start')
    end = request.args.get('end')
    if not start or not end:
        flash("Période invalide.", "warning")
        return redirect(url_for('reports'))
    rows = query_sales_between(start, end)
    si = StringIO()
    writer = csv.writer(si, delimiter=';')
    writer.writerow(['ID Vente', 'Date', 'Client', 'Montant'])
    total = 0.0
    for r in rows:
        total += r['amount'] or 0.0
        writer.writerow([r['id'], r['created_at'], r['client_name'] or '', f"{r['amount']:.2f}"])
    writer.writerow([])
    writer.writerow(['', '', 'Total', f"{total:.2f}"])
    output = si.getvalue()
    return send_file(BytesIO(output.encode('utf-8-sig')), as_attachment=True,
                     download_name=f"rapport_ventes_{start}_au_{end}.csv",
                     mimetype='text/csv; charset=utf-8')

@app.route('/reports/download/pdf')
@login_required
def report_pdf():
    start = request.args.get('start')
    end = request.args.get('end')
    if not start or not end:
        flash("Période invalide.", "warning")
        return redirect(url_for('reports'))
    rows = query_sales_between(start, end)
    total = sum([r['amount'] or 0.0 for r in rows])

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Rapport des ventes")
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(50, y, f"Période: {start} au {end}")
    y -= 30

    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, "ID")
    p.drawString(100, y, "Date")
    p.drawString(220, y, "Client")
    p.drawString(420, y, "Montant")
    y -= 15
    p.line(50, y, width - 50, y)
    y -= 10

    p.setFont("Helvetica", 10)
    for r in rows:
        if y < 80:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 11)
            p.drawString(50, y, "ID")
            p.drawString(100, y, "Date")
            p.drawString(220, y, "Client")
            p.drawString(420, y, "Montant")
            y -= 15
            p.line(50, y, width - 50, y)
            y -= 10
            p.setFont("Helvetica", 10)
        p.drawString(50, y, str(r['id']))
        p.drawString(100, y, r['created_at'][:19])
        p.drawString(220, y, (r['client_name'] or '')[:28])
        p.drawRightString(500, y, f"{r['amount']:.2f} €")
        y -= 16

    y -= 10
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(500, y, f"Total: {total:.2f} €")

    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"rapport_ventes_{start}_au_{end}.pdf",
                     mimetype='application/pdf')

# Simple route to change password (optional)
@app.route('/account/password', methods=['GET','POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form.get('current','')
        new = request.form.get('new','')
        confirm = request.form.get('confirm','')
        if not new or new != confirm:
            flash("Les nouveaux mots de passe ne correspondent pas.", "warning")
            return render_template('change_password.html')
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
        user = cur.fetchone()
        if not user or not check_password_hash(user['password_hash'], current):
            conn.close()
            flash("Mot de passe actuel incorrect.", "danger")
            return render_template('change_password.html')
        cur.execute("UPDATE users SET password_hash=? WHERE id=?",
                    (generate_password_hash(new), session['user_id']))
        conn.commit()
        conn.close()
        flash("Mot de passe modifié.", "success")
        return redirect(url_for('dashboard'))
    return render_template('change_password.html')

if __name__ == '__main__':
    # Pour activer HTTPS en dev, on peut utiliser un proxy ou cert adhoc.
    # Ici on lance en debug http simple. En prod, utiliser un serveur WSGI et config HTTPS.
    app.run(debug=True)

Templates:

templates/layout.html:
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Admin - PME</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg bg-dark navbar-dark">
  <div class="container-fluid">
    <a class="navbar-brand" href="{{ url_for('dashboard') }}">PME Admin</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarsExample">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarsExample">
      <ul class="navbar-nav me-auto mb-2 mb-lg-0">
        {% if session.get('user_id') %}
        <li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Tableau de bord</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('employees_list') }}">Employés</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('uploads') }}">Fichiers</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('reports') }}">Rapports</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('change_password') }}">Mon compte</a></li>
        {% endif %}
      </ul>
      <ul class="navbar-nav ms-auto">
        {% if session.get('user_id') %}
        <li class="nav-item"><span class="navbar-text me-3">Connecté: {{ session.get('username') }}</span></li>
        <li class="nav-item"><a class="btn btn-outline-light btn-sm" href="{{ url_for('logout') }}">Déconnexion</a></li>
        {% endif %}
      </ul>
    </div>
  </div>
</nav>
<main class="container my-4">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
      <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
        {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  {% block content %}{% endblock %}
</main>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>

templates/login.html:
{% extends "layout.html" %}
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-4">
    <h3 class="mb-3">Connexion</h3>
    <form method="post">
      <div class="mb-3">
        <label class="form-label">Utilisateur</label>
        <input type="text" name="username" class="form-control" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Mot de passe</label>
        <input type="password" name="password" class="form-control" required>
      </div>
      <button class="btn btn-primary w-100">Se connecter</button>
    </form>
  </div>
</div>
{% endblock %}

templates/dashboard.html:
{% extends "layout.html" %}
{% block content %}
<h3>Tableau de bord</h3>
<div class="row g-3">
  <div class="col-md-3">
    <div class="card text-bg-primary">
      <div class="card-body">
        <h6 class="card-title">Chiffre d'affaires total</h6>
        <p class="card-text fs-4">{{ '%.2f'|format(total_revenue) }} €</p>
      </div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card text-bg-success">
      <div class="card-body">
        <h6 class="card-title">Clients</h6>
        <p class="card-text fs-4">{{ client_count }}</p>
      </div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card text-bg-info">
      <div class="card-body">
        <h6 class="card-title">Ventes du mois (nb)</h6>
        <p class="card-text fs-4">{{ sales_count_month }}</p>
      </div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card text-bg-warning">
      <div class="card-body">
        <h6 class="card-title">Ventes du mois (montant)</h6>
        <p class="card-text fs-4">{{ '%.2f'|format(sales_amount_month) }} €</p>
      </div>
    </div>
  </div>
</div>
{% endblock %}

templates/employees.html:
{% extends "layout.html" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center">
  <h3>Employés</h3>
  <a class="btn btn-primary" href="{{ url_for('employee_add') }}">+ Ajouter</a>
</div>
<form class="row g-2 my-3" method="get">
  <div class="col-auto">
    <input class="form-control" type="search" name="q" placeholder="Recherche..." value="{{ q }}">
  </div>
  <div class="col-auto">
    <button class="btn btn-outline-secondary">Rechercher</button>
  </div>
</form>
<div class="table-responsive">
<table class="table table-striped align-middle">
  <thead>
    <tr>
      <th>ID</th><th>Nom</th><th>Email</th><th>Rôle</th><th>Salaire</th><th>Embauché</th><th></th>
    </tr>
  </thead>
  <tbody>
    {% for e in employees %}
    <tr>
      <td>{{ e.id }}</td>
      <td>{{ e.first_name }} {{ e.last_name }}</td>
      <td>{{ e.email }}</td>
      <td>{{ e.role }}</td>
      <td>{{ '%.2f'|format(e.salary or 0) }} €</td>
      <td>{{ e.hired_at[:10] }}</td>
      <td class="text-end">
        <a class="btn btn-sm btn-outline-primary" href="{{ url_for('employee_edit', emp_id=e.id) }}">Modifier</a>
        <form action="{{ url_for('employee_delete', emp_id=e.id) }}" method="post" class="d-inline" onsubmit="return confirm('Supprimer cet employé ?');">
          <button class="btn btn-sm btn-outline-danger">Supprimer</button>
        </form>
      </td>
    </tr>
    {% else %}
    <tr><td colspan="7">Aucun employé.</td></tr>
    {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}

templates/employee_form.html:
{% extends "layout.html" %}
{% block content %}
<h3>{{ 'Ajouter un employé' if action == 'add' else 'Modifier un employé' }}</h3>
<form method="post" class="row g-3">
  <div class="col-md-6">
    <label class="form-label">Prénom</label>
    <input class="form-control" name="first_name" required value="{{ emp.first_name if emp else '' }}">
  </div>
  <div class="col-md-6">
    <label class="form-label">Nom</label>
    <input class="form-control" name="last_name" required value="{{ emp.last_name if emp else '' }}">
  </div>
  <div class="col-md-6">
    <label class="form-label">Email</label>
    <input type="email" class="form-control" name="email" required value="{{ emp.email if emp else '' }}">
  </div>
  <div class="col-md-6">
    <label class="form-label">Rôle</label>
    <input class="form-control" name="role" value="{{ emp.role if emp else '' }}">
  </div>
  <div class="col-md-6">
    <label class="form-label">Salaire</label>
    <input class="form-control" name="salary" type="number" step="0.01" value="{{ emp.salary if emp else '' }}">
  </div>
  <div class="col-12">
    <button class="btn btn-primary">Enregistrer</button>
    <a class="btn btn-secondary" href="{{ url_for('employees_list') }}">Annuler</a>
  </div>
</form>
{% endblock %}

templates/uploads.html:
{% extends "layout.html" %}
{% block content %}
<h3>Fichiers (factures, images)</h3>
<form method="post" enctype="multipart/form-data" class="my-3">
  <div class="input-group">
    <input type="file" class="form-control" name="file" accept=".pdf,image/*" required>
    <button class="btn btn-primary">Uploader</button>
  </div>
  <div class="form-text">Extensions autorisées: pdf, png, jpg, jpeg, gif</div>
</form>
<div class="table-responsive">
<table class="table table-striped align-middle">
  <thead>
    <tr><th>ID</th><th>Nom</th><th>Type</th><th>Date</th><th></th></tr>
  </thead>
  <tbody>
    {% for f in files %}
    <tr>
      <td>{{ f.id }}</td>
      <td>{{ f.original_name }}</td>
      <td>{{ f.mimetype }}</td>
      <td>{{ f.uploaded_at[:19] }}</td>
      <td class="text-end">
        <a class="btn btn-sm btn-outline-success" href="{{ url_for('download_file', file_id=f.id) }}">Télécharger</a>
        <form action="{{ url_for('delete_file', file_id=f.id) }}" method="post" class="d-inline" onsubmit="return confirm('Supprimer ce fichier ?');">
          <button class="btn btn-sm btn-outline-danger">Supprimer</button>
        </form>
      </td>
    </tr>
    {% else %}
    <tr><td colspan="5">Aucun fichier.</td></tr>
    {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}

templates/reports.html:
{% extends "layout.html" %}
{% block content %}
<h3>Rapports</h3>
<form class="row gy-2 gx-3 align-items-end" method="get" action="{{ url_for('report_csv') }}">
  <div class="col-auto">
    <label class="form-label">Début</label>
    <input type="date" class="form-control" name="start" value="{{ default_start }}">
  </div>
  <div class="col-auto">
    <label class="form-label">Fin</label>
    <input type="date" class="form-control" name="end" value="{{ default_end }}">
  </div>
  <div class="col-auto">
    <button class="btn btn-outline-primary">Télécharger CSV</button>
  </div>
</form>
<form class="row gy-2 gx-3 align-items-end mt-3" method="get" action="{{ url_for('report_pdf') }}">
  <div class="col-auto">
    <label class="form-label">Début</label>
    <input type="date" class="form-control" name="start" value="{{ default_start }}">
  </div>
  <div class="col-auto">
    <label class="form-label">Fin</label>
    <input type="date" class="form-control" name="end" value="{{ default_end }}">
  </div>
  <div class="col-auto">
    <button class="btn btn-outline-danger">Télécharger PDF</button>
  </div>
</form>
{% endblock %}

templates/change_password.html:
{% extends "layout.html" %}
{% block content %}
<h3>Changer le mot de passe</h3>
<form method="post" class="row g-3">
  <div class="col-md-6">
    <label class="form-label">Mot de passe actuel</label>
    <input type="password" name="current" class="form-control" required>
  </div>
  <div class="col-md-6">
    <label class="form-label">Nouveau mot de passe</label>
    <input type="password" name="new" class="form-control" required>
  </div>
  <div class="col-md-6">
    <label class="form-label">Confirmer</label>
    <input type="password" name="confirm" class="form-control" required>
  </div>
  <div class="col-12">
    <button class="btn btn-primary">Mettre à jour</button>
  </div>
</form>
{% endblock %}

Notes de sécurité et déploiement:
- Changez SECRET_KEY et le mot de passe admin par défaut.
- Limitez la taille des uploads: app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
- Filtrez davantage les types de fichiers si besoin (vérification MIME).
- Servez l’application derrière un serveur WSGI (gunicorn/uwsgi) et un reverse proxy HTTPS (Nginx/Caddy).
- Activez SameSite/HttpOnly pour les cookies de session (Flask le fait pour HttpOnly par défaut; configurez SESSION_COOKIE_SAMESITE='Lax' ou 'Strict', SESSION_COOKIE_SECURE=True en prod).