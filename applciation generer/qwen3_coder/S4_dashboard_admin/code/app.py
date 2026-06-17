import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pandas as pd

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Création de la base de données
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    position TEXT,
                    salary REAL)''')

    c.execute('''CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL,
                    date TEXT)''')

    # Insertion utilisateur admin par défaut
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "password"))
    except:
        pass

    conn.commit()
    conn.close()

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            login_user(User(user[0], user[1]))
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiants incorrects.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Stats
    c.execute("SELECT COUNT(*) FROM employees")
    nb_employees = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM sales")
    nb_sales = c.fetchone()[0]

    c.execute("SELECT SUM(amount) FROM sales")
    total_revenue = c.fetchone()[0] or 0

    this_month = datetime.now().strftime("%Y-%m")
    c.execute("SELECT SUM(amount) FROM sales WHERE date LIKE ?", (this_month + "%",))
    monthly_revenue = c.fetchone()[0] or 0

    conn.close()

    return render_template(
        'dashboard.html',
        nb_employees=nb_employees,
        nb_sales=nb_sales,
        total_revenue=total_revenue,
        monthly_revenue=monthly_revenue
    )

@app.route('/employees', methods=['GET', 'POST'])
@login_required
def employees():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        position = request.form['position']
        salary = float(request.form['salary'])
        c.execute("INSERT INTO employees (name, position, salary) VALUES (?, ?, ?)", (name, position, salary))
        conn.commit()
        flash("Employé ajouté.")
    c.execute("SELECT * FROM employees")
    employees_list = c.fetchall()
    conn.close()
    return render_template('employees.html', employees=employees_list)

@app.route('/delete_employee/<int:id>')
@login_required
def delete_employee(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Employé supprimé.")
    return redirect(url_for('employees'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné.')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('Aucun fichier sélectionné.')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash("Fichier téléchargé.")
        return redirect(url_for('dashboard'))
    else:
        flash("Type de fichier non autorisé.")
        return redirect(request.url)

@app.route('/report')
@login_required
def report():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT * FROM sales", conn)
    conn.close()
    output_path = 'static/report.csv'
    df.to_csv(output_path, index=False)
    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    init_db()
    app.run(debug=True)
