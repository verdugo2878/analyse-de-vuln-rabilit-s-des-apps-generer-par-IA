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
