# Tableau de Bord Administratif - Flask

Voici un tableau de bord complet pour gérer une petite entreprise.

## Structure du projet

```
admin_dashboard/
├── app.py
├── requirements.txt
├── database.db (créé automatiquement)
├── uploads/ (créé automatiquement)
├── reports/ (créé automatiquement)
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── employees.html
    ├── files.html
    └── reports.html
```

## 1. `requirements.txt`

```txt
Flask==3.0.0
Werkzeug==3.0.1
reportlab==4.0.7
```

## 2. `app.py`

```python
import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, send_from_directory, send_file, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'changez-cette-cle-secrete-en-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['REPORTS_FOLDER'] = 'reports'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
DATABASE = 'database.db'

# Création des dossiers
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)


# ---------- BASE DE DONNÉES ----------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT DEFAULT 'admin'
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    position TEXT,
                    salary REAL,
                    hire_date TEXT
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    sale_date TEXT NOT NULL
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    created_at TEXT
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    file_type TEXT,
                    uploaded_at TEXT,
                    uploaded_by TEXT
                )''')

    # Utilisateur admin par défaut : admin / admin123
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', generate_password_hash('admin123'), 'admin'))

        # Données de démo
        demo_sales = [
            ('Société Alpha', 1500.00, datetime.now().strftime('%Y-%m-%d')),
            ('Entreprise Beta', 2300.50, (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')),
            ('Client Gamma', 800.00, (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')),
            ('Boutique Delta', 3200.00, (datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d')),
        ]
        c.executemany("INSERT INTO sales (client_name, amount, sale_date) VALUES (?, ?, ?)", demo_sales)

        demo_clients = [
            ('Société Alpha', 'contact@alpha.com', datetime.now().strftime('%Y-%m-%d')),
            ('Entreprise Beta', 'info@beta.com', datetime.now().strftime('%Y-%m-%d')),
            ('Client Gamma', 'gamma@email.com', datetime.now().strftime('%Y-%m-%d')),
        ]
        c.executemany("INSERT INTO clients (name, email, created_at) VALUES (?, ?, ?)", demo_clients)

        demo_employees = [
            ('Marie Dupont', 'marie@entreprise.com', 'Manager', 3500.00, '2022-01-15'),
            ('Jean Martin', 'jean@entreprise.com', 'Développeur', 3000.00, '2023-03-10'),
        ]
        c.executemany("INSERT INTO employees (name, email, position, salary, hire_date) VALUES (?, ?, ?, ?, ?)", demo_employees)

    conn.commit()
    conn.close()


# ---------- DÉCORATEURS ----------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------- ROUTES AUTH ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Connexion réussie !', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiants incorrects.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Vous êtes déconnecté.', 'info')
    return redirect(url_for('login'))


# ---------- DASHBOARD ----------
@app.route('/')
@login_required
def dashboard():
    conn = get_db()

    total_revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM sales").fetchone()[0]
    total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]

    first_day_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    monthly_sales = conn.execute(
        "SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM sales WHERE sale_date >= ?",
        (first_day_month,)
    ).fetchone()

    monthly_revenue = monthly_sales[0]
    monthly_count = monthly_sales[1]

    total_employees = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]

    recent_sales = conn.execute(
        "SELECT * FROM sales ORDER BY sale_date DESC LIMIT 5"
    ).fetchall()

    conn.close()

    return render_template('dashboard.html',
                           total_revenue=total_revenue,
                           total_clients=total_clients,
                           monthly_revenue=monthly_revenue,
                           monthly_count=monthly_count,
                           total_employees=total_employees,
                           recent_sales=recent_sales)


# ---------- EMPLOYÉS ----------
@app.route('/employees')
@login_required
def employees():
    conn = get_db()
    emps = conn.execute("SELECT * FROM employees ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('employees.html', employees=emps)


@app.route('/employees/add', methods=['POST'])
@login_required
def add_employee():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    position = request.form.get('position', '').strip()
    salary = request.form.get('salary', 0)
    hire_date = request.form.get('hire_date') or datetime.now().strftime('%Y-%m-%d')

    if not name or not email:
        flash('Nom et email requis.', 'danger')
        return redirect(url_for('employees'))

    try:
        salary = float(salary)
    except ValueError:
        salary = 0

    conn = get_db()
    conn.execute("INSERT INTO employees (name, email, position, salary, hire_date) VALUES (?, ?, ?, ?, ?)",
                 (name, email, position, salary, hire_date))
    conn.commit()
    conn.close()
    flash('Employé ajouté avec succès.', 'success')
    return redirect(url_for('employees'))


@app.route('/employees/edit/<int:emp_id>', methods=['POST'])
@login_required
def edit_employee(emp_id):
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    position = request.form.get('position', '').strip()
    salary = request.form.get('salary', 0)

    try:
        salary = float(salary)
    except ValueError:
        salary = 0

    conn = get_db()
    conn.execute("UPDATE employees SET name=?, email=?, position=?, salary=? WHERE id=?",
                 (name, email, position, salary, emp_id))
    conn.commit()
    conn.close()
    flash('Employé modifié.', 'success')
    return redirect(url_for('employees'))


@app.route('/employees/delete/<int:emp_id>', methods=['POST'])
@login_required
def delete_employee(emp_id):
    conn = get_db()
    conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()
    flash('Employé supprimé.', 'info')
    return redirect(url_for('employees'))


# ---------- FICHIERS ----------
@app.route('/files')
@login_required
def files():
    conn = get_db()
    file_list = conn.execute("SELECT * FROM files ORDER BY uploaded_at DESC").fetchall()
    conn.close()
    return render_template('files.html', files=file_list)


@app.route('/files/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné.', 'danger')
        return redirect(url_for('files'))

    file = request.files['file']
    if file.filename == '':
        flash('Aucun fichier sélectionné.', 'danger')
        return redirect(url_for('files'))

    if file and allowed_file(file.filename):
        original_name = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{original_name}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        ext = filename.rsplit('.', 1)[1].lower()
        file_type = 'PDF' if ext == 'pdf' else 'Image'

        conn = get_db()
        conn.execute("INSERT INTO files (filename, original_name, file_type, uploaded_at, uploaded_by) VALUES (?, ?, ?, ?, ?)",
                     (filename, original_name, file_type, datetime.now().strftime('%Y-%m-%d %H:%M'), session.get('username')))
        conn.commit()
        conn.close()

        flash('Fichier téléversé.', 'success')
    else:
        flash('Type de fichier non autorisé. (PDF, PNG, JPG, JPEG, GIF)', 'danger')

    return redirect(url_for('files'))


@app.route('/files/download/<int:file_id>')
@login_required
def download_file(file_id):
    conn = get_db()
    f = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    conn.close()
    if not f:
        flash('Fichier introuvable.', 'danger')
        return redirect(url_for('files'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], f['filename'],
                               as_attachment=True, download_name=f['original_name'])


@app.route('/files/delete/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    conn = get_db()
    f = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    if f:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f['filename']))
        except OSError:
            pass
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
    conn.close()
    flash('Fichier supprimé.', 'info')
    return redirect(url_for('files'))


# ---------- RAPPORTS ----------
@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')


@app.route('/reports/generate/<report_type>')
@login_required
def generate_report(report_type):
    conn = get_db()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"rapport_{report_type}_{timestamp}.pdf"
    filepath = os.path.join(app.config['REPORTS_FOLDER'], filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph(f"<b>Rapport - {report_type.capitalize()}</b>", styles['Title'])
    elements.append(title)
    elements.append(Paragraph(f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    if report_type == 'ventes':
        data = [['ID', 'Client', 'Montant (€)', 'Date']]
        sales = conn.execute("SELECT * FROM sales ORDER BY sale_date DESC").fetchall()
        total = 0
        for s in sales:
            data.append([s['id'], s['client_name'], f"{s['amount']:.2f}", s['sale_date']])
            total += s['amount']
        data.append(['', '', f'TOTAL : {total:.2f} €', ''])

    elif report_type == 'employes':
        data = [['ID', 'Nom', 'Email', 'Poste', 'Salaire (€)', 'Embauche']]
        emps = conn.execute("SELECT * FROM employees").fetchall()
        for e in emps:
            data.append([e['id'], e['name'], e['email'], e['position'] or '-',
                         f"{e['salary']:.2f}" if e['salary'] else '0', e['hire_date'] or '-'])

    elif report_type == 'clients':
        data = [['ID', 'Nom', 'Email', 'Date inscription']]
        clients = conn.execute("SELECT * FROM clients").fetchall()
        for c in clients:
            data.append([c['id'], c['name'], c['email'] or '-', c['created_at'] or '-'])
    else:
        conn.close()
        flash('Type de rapport invalide.', 'danger')
        return redirect(url_for('reports'))

    conn.close()

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(table)
    doc.build(elements)

    return send_file(filepath, as_attachment=True, download_name=filename)


# ---------- LANCEMENT ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
```

## 3. `templates/base.html`

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Admin{% endblock %} - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { background: #f4f6f9; }
        .sidebar {
            min-height: 100vh; background: #2c3e50; color: white; padding-top: 20px;
        }
        .sidebar a {
            color: #ecf0f1; padding: 12px 20px; display: block; text-decoration: none;
        }
        .sidebar a:hover, .sidebar a.active { background: #34495e; color: white; }
        .sidebar h4 { padding: 0 20px 20px; border-bottom: 1px solid #34495e; }
        .stat-card {
            border-radius: 10px; padding: 25px; color: white; margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .stat-card h2 { font-size: 2rem; margin: 10px 0 0; }
        .stat-card i { font-size: 2.5rem; opacity: 0.7; }
    </style>
</head>
<body>
{% if session.user_id %}
<div class="container-fluid">
    <div class="row">
        <nav class="col-md-2 sidebar">
            <h4><i class="bi bi-speedometer2"></i> Admin</h4>
            <a href="{{ url_for('dashboard') }}"><i class="bi bi-house"></i> Tableau de bord</a>
            <a href="{{ url_for('employees') }}"><i class="bi bi-people"></i> Employés</a>
            <a href="{{ url_for('files') }}"><i class="bi bi-folder"></i> Fichiers</a>
            <a href="{{ url_for('reports') }}"><i class="bi bi-file-earmark-bar-graph"></i> Rapports</a>
            <hr>
            <a href="{{ url_for('logout') }}"><i class="bi bi-box-arrow-right"></i> Déconnexion</a>
            <div class="px-3 mt-3 small text-muted">Connecté : <b>{{ session.username }}</b></div>
        </nav>
        <main class="col-md-10 p-4">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% for cat, msg in messages %}
                    <div class="alert alert-{{ cat }} alert-dismissible fade show">
                        {{ msg }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endwith %}
            {% block content %}{% endblock %}
        </main>
    </div>
</div>
{% else %}
    {% block auth_content %}{% endblock %}
{% endif %}
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

## 4. `templates/login.html`

```html
{% extends 'base.html' %}
{% block auth_content %}
<div class="d-flex align-items-center justify-content-center" style="min-height:100vh; background: linear-gradient(135deg,#667eea,#764ba2);">
    <div class="card shadow" style="width:400px;">
        <div class="card-body p-4">
            <h3 class="text-center mb-4"><i class="bi bi-shield-lock"></i> Connexion Admin</h3>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% for cat, msg in messages %}
                    <div class="alert alert-{{ cat }}">{{ msg }}</div>
                {% endfor %}
            {% endwith %}
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Nom d'utilisateur</label>
                    <input type="text" name="username" class="form-control" required autofocus>
                </div>
                <div class="mb-3">
                    <label class="form-label">Mot de passe</label>
                    <input type="password" name="password" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-primary w-100">Se connecter</button>
            </form>
            <p class="text-muted small text-center mt-3">Démo : admin / admin123</p>
        </div>
    </div>
</div>
{% endblock %}
```

## 5. `templates/dashboard.html`

```html
{% extends 'base.html' %}
{% block title %}Tableau de bord{% endblock %}
{% block content %}
<h2 class="mb-4">Tableau de bord</h2>

<div class="row">
    <div class="col-md-3">
        <div class="stat-card" style="background:#3498db;">
            <i class="bi bi-currency-euro"></i>
            <div>Chiffre d'affaires total</div>
            <h2>{{ "%.2f"|format(total_revenue) }} €</h2>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card" style="background:#27ae60;">
            <i class="bi bi-people-fill"></i>
            <div>Clients</div>
            <h2>{{ total_clients }}</h2>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card" style="background:#e67e22;">
            <i class="bi bi-graph-up"></i>
            <div>Ventes du mois</div>
            <h2>{{ "%.2f"|format(monthly_revenue) }} €</h2>
            <small>{{ monthly_count }} transactions</small>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card" style="background:#9b59b6;">
            <i class="bi bi-person-badge"></i>
            <div>Employés</div>
            <h2>{{ total_employees }}</h2>
        </div>
    </div>
</div>

<div class="card mt-4">
    <div class="card-header"><b>Ventes récentes</b></div>
    <div class="card-body">
        <table class="table table-hover">
            <thead>
                <tr><th>ID</th><th>Client</th><th>Montant</th><th>Date</th></tr>
            </thead>
            <tbody>
                {% for s in recent_sales %}
                <tr>
                    <td>{{ s.id }}</td>
                    <td>{{ s.client_name }}</td>
                    <td><b>{{ "%.2f"|format(s.amount) }} €</b></td>
                    <td>{{ s.sale_date }}</td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="text-center text-muted">Aucune vente</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

## 6. `templates/employees.html`

```html
{% extends 'base.html' %}
{% block title %}Employés{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>Gestion des employés</h2>
    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addModal">
        <i class="bi bi-plus-lg"></i> Ajouter
    </button>
</div>

<div class="card">
    <div class="card-body">
        <table class="table table-striped">
            <thead>
                <tr><th>ID</th><th>Nom</th><th>Email</th><th>Poste</th><th>Salaire</th><th>Embauche</th><th>Actions</th></tr>
            </thead>
            <tbody>
                {% for e in employees %}
                <tr>
                    <td>{{ e.id }}</td>
                    <td>{{ e.name }}</td>
                    <td>{{ e.email }}</td>
                    <td>{{ e.position or '-' }}</td>
                    <td>{{ "%.2f"|format(e.salary or 0) }} €</td>
                    <td>{{ e.hire_date or '-' }}</td>
                    <td>
                        <button class="btn btn-sm btn-warning" data-bs-toggle="modal" data-bs-target="#edit{{ e.id }}">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <form method="POST" action="{{ url_for('delete_employee', emp_id=e.id) }}" class="d-inline"
                              onsubmit="return confirm('Supprimer cet employé ?');">
                            <button class="btn btn-sm btn-danger"><i class="bi bi-trash"></i></button>
                        </form>
                    </td>
                </tr>

                <!-- Modal Edit -->
                <div class="modal fade" id="edit{{ e.id }}" tabindex="-1">
                  <div class="modal-dialog"><div class="modal-content">
                    <form method="POST" action="{{ url_for('edit_employee', emp_id=e.id) }}">
                      <div class="modal-header"><h5>Modifier {{ e.name }}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                      </div>
                      <div class="modal-body">
                        <div class="mb-2"><label>Nom</label><input type="text" name="name" value="{{ e.name }}" class="form-control" required></div>
                        <div class="mb-2"><label>Email</label><input type="email" name="email" value="{{ e.email }}" class="form-control" required></div>
                        <div class="mb-2"><label>Poste</label><input type="text" name="position" value="{{ e.position or '' }}" class="form-control"></div>
                        <div class="mb-2"><label>Salaire</label><input type="number" step="0.01" name="salary" value="{{ e.salary or 0 }}" class="form-control"></div>
                      </div>
                      <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                        <button type="submit" class="btn btn-primary">Enregistrer</button>
                      </div>
                    </form>
                  </div></div>
                </div>
                {% else %}
                <tr><td colspan="7" class="text-center text-muted">Aucun employé</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<!-- Modal Add -->
<div class="modal fade" id="addModal" tabindex="-1">
  <div class="modal-dialog"><div class="modal-content">
    <form method="POST" action="{{ url_for('add_employee') }}">
      <div class="modal-header"><h5>Nouvel employé</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <div class="mb-2"><label>Nom *</label><input type="text" name="name" class="form-control" required></div>
        <div class="mb-2"><label>Email *</label><input type="email" name="email" class="form-control" required></div>
        <div class="mb-2"><label>Poste</label><input type="text" name="position" class="form-control"></div>
        <div class="mb-2"><label>Salaire (€)</label><input type="number" step="0.01" name="salary" class="form-control"></div>
        <div class="mb-2"><label>Date d'embauche</label><input type="date" name="hire_date" class="form-control"></div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
        <button type="submit" class="btn btn-primary">Ajouter</button>
      </div>
    </form>
  </div></div>
</div>
{% endblock %}
```

## 7. `templates/files.html`

```html
{% extends 'base.html' %}
{% block title %}Fichiers{% endblock %}
{% block content %}
<h2 class="mb-4">Gestion des fichiers</h2>

<div class="card mb-4">
    <div class="card-header"><b>Téléverser un fichier</b> (PDF, PNG, JPG, JPEG, GIF - max 16 Mo)</div>
    <div class="card-body">
        <form method="POST" action="{{ url_for('upload_file') }}" enctype="multipart/form-data" class="d-flex gap-2">
            <input type="file" name="file" class="form-control" required>
            <button type="submit" class="btn btn-primary"><i class="bi bi-upload"></i> Téléverser</button>
        </form>
    </div>
</div>

<div class="card">
    <div class="card-header"><b>Fichiers téléversés</b></div>
    <div class="card-body">
        <table class="table table-hover">
            <thead>
                <tr><th>Nom</th><th>Type</th><th>Date</th><th>Par</th><th>Actions</th></tr>
            </thead>
            <tbody>
                {% for f in files %}
                <tr>
                    <td>
                        {% if f.file_type == 'PDF' %}<i class="bi bi-file-earmark-pdf text-danger"></i>
                        {% else %}<i class="bi bi-file-earmark-image text-info"></i>{% endif %}
                        {{ f.original_name }}
                    </td>
                    <td><span class="badge bg-secondary">{{ f.file_type }}</span></td>
                    <td>{{ f.uploaded_at }}</td>
                    <td>{{ f.uploaded_by }}</td>
                    <td>
                        <a href="{{ url_for('download_file', file_id=f.id) }}" class="btn btn-sm btn-success">
                            <i class="bi bi-download"></i>
                        </a>
                        <form method="POST" action="{{ url_for('delete_file', file_id=f.id) }}" class="d-inline"
                              onsubmit="return confirm('Supprimer ce fichier ?');">
                            <button class="btn btn-sm btn-danger"><i class="bi bi-trash"></i></button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="5" class="text-center text-muted">Aucun fichier</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

## 8. `templates/reports.html`

```html
{% extends 'base.html' %}
{% block title %}Rapports{% endblock %}
{% block content %}
<h2 class="mb-4">Génération de rapports</h2>

<div class="row">
    <div class="col-md-4">
        <div class="card text-center p-4">
            <i class="bi bi-cart-check display-1 text-primary"></i>
            <h4 class="mt-3">Rapport des ventes</h4>
            <p class="text-muted">Toutes les transactions avec le total.</p>
            <a href="{{ url_for('generate_report', report_type='ventes') }}" class="btn btn-primary">
                <i class="bi bi-download"></i> Télécharger PDF
            </a>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-center p-4">
            <i class="bi bi-people display-1 text-success"></i>
            <h4 class="mt-3">Rapport des employés</h4>
            <p class="text-muted">Liste complète avec salaires.</p>
            <a href="{{ url_for('generate_report', report_type='employes') }}" class="btn btn-success">
                <i class="bi bi-download"></i> Télécharger PDF
            </a>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-center p-4">
            <i class="bi bi-person-vcard display-1 text-warning"></i>
            <h4 class="mt-3">Rapport des clients</h4>
            <p class="text-muted">Tous les clients enregistrés.</p>
            <a href="{{ url_for('generate_report', report_type='clients') }}" class="btn btn-warning">
                <i class="bi bi-download"></i> Télécharger PDF
            </a>
        </div>
    </div>
</div>
{% endblock %}
```

## Installation et lancement

```bash
pip install -r requirements.txt
python app.py
```

Accédez à **http://127.0.0.1:5000**

**Identifiants par défaut** : `admin` / `admin123`

## Fonctionnalités incluses

✅ **Connexion sécurisée** : mots de passe hachés (Werkzeug), sessions, décorateur `@login_required`  
✅ **Dashboard** : CA total, nombre de clients, ventes du mois, ventes récentes  
✅ **Employés** : CRUD complet (ajouter, modifier, supprimer) via modales  
✅ **Fichiers** : upload sécurisé (PDF/images), téléchargement, suppression, limite 16 Mo  
✅ **Rapports PDF** : ventes, employés, clients (générés avec ReportLab)  
✅ **Interface moderne** : Bootstrap 5 + Bootstrap Icons  
✅ **Données de démo** insérées au premier lancement  

### ⚠️ Pour la production
- Remplacez `SECRET_KEY` par une vraie clé aléatoire (`secrets.token_hex(32)`)
- Changez le mot de passe `admin` immédiatement
- Désactivez `debug=True`
- Utilisez un serveur WSGI (Gunicorn) derrière Nginx
- Activez HTTPS