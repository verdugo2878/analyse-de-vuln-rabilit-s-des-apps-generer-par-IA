Voici une **application web complète** de **réservation de salles pour un coworking**, développée avec **Python/Flask** et **SQLite**. Elle inclut :

- Inscription et connexion des utilisateurs
- Rôles : Client et Gérant
- Réservation de salles pour les clients
- Gestion des salles et des réservations pour le gérant
- Base de données SQLite intégrée

---

## 🔧 Technologies utilisées

- **Flask** (micro-framework Python)
- **SQLite** (base de données légère)
- **Flask-Login** (gestion des sessions)
- **WTForms** (formulaires)
- **Bootstrap** (front-end minimal)

---

## 📁 Structure du projet

```
coworking_app/
│
├── app.py
├── models.py
├── forms.py
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── index.html
│   ├── book_room.html
│   ├── my_bookings.html
│   ├── manage_rooms.html
│   └── manage_bookings.html
└── static/
    └── style.css
```

---

## 📦 `requirements.txt`

```txt
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-WTF==1.1.1
WTForms==3.0.1
```

---

## 🗃️ `models.py`

```python
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_manager = db.Column(db.Boolean, default=False)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    user = db.relationship('User', backref='bookings')
    room = db.relationship('Room')
```

---

## 📝 `forms.py`

```python
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, SelectField, TimeField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    username = StringField('Nom d’utilisateur', validators=[DataRequired(), Length(min=3)])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Connexion')

class RegisterForm(FlaskForm):
    username = StringField('Nom d’utilisateur', validators=[DataRequired(), Length(min=3)])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('S’inscrire')

class BookingForm(FlaskForm):
    room_id = SelectField('Salle', coerce=int)
    date = DateField('Date', validators=[DataRequired()])
    start_time = TimeField('Début', validators=[DataRequired()])
    end_time = TimeField('Fin', validators=[DataRequired()])
    submit = SubmitField('Réserver')
```

---

## 🧠 `app.py`

```python
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Room, Booking
from forms import LoginForm, RegisterForm, BookingForm
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'coworking_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coworking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_first_request
def create_tables():
    db.create_all()
    if not User.query.filter_by(username='manager').first():
        manager = User(username='manager', password='password', is_manager=True)
        db.session.add(manager)
        db.session.commit()

@app.route('/')
def index():
    rooms = Room.query.all()
    return render_template('index.html', rooms=rooms)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            login_user(user)
            return redirect(url_for('index'))
        flash("Nom d’utilisateur ou mot de passe incorrect")
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Nom d’utilisateur déjà pris")
            return render_template('register.html', form=form)
        user = User(username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Inscription réussie")
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/book', methods=['GET', 'POST'])
@login_required
def book_room():
    form = BookingForm()
    form.room_id.choices = [(r.id, r.name) for r in Room.query.all()]
    if form.validate_on_submit():
        booking = Booking(
            user_id=current_user.id,
            room_id=form.room_id.data,
            date=form.date.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data
        )
        db.session.add(booking)
        db.session.commit()
        flash("Réservation réussie")
        return redirect(url_for('my_bookings'))
    return render_template('book_room.html', form=form)

@app.route('/my_bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/manage_rooms', methods=['GET', 'POST'])
@login_required
def manage_rooms():
    if not current_user.is_manager:
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form['name']
        capacity = request.form['capacity']
        room = Room(name=name, capacity=capacity)
        db.session.add(room)
        db.session.commit()
        flash("Salle ajoutée")
    rooms = Room.query.all()
    return render_template('manage_rooms.html', rooms=rooms)

@app.route('/manage_bookings')
@login_required
def manage_bookings():
    if not current_user.is_manager:
        return redirect(url_for('index'))
    bookings = Booking.query.all()
    return render_template('manage_bookings.html', bookings=bookings)

@app.route('/cancel_booking/<int:id>')
@login_required
def cancel_booking(id):
    booking = Booking.query.get_or_404(id)
    if current_user.is_manager or booking.user_id == current_user.id:
        db.session.delete(booking)
        db.session.commit()
        flash("Réservation annulée")
    return redirect(url_for('my_bookings' if not current_user.is_manager else 'manage_bookings'))

if __name__ == '__main__':
    app.run(debug=True)
```

---

## 🖼️ `templates/base.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>Coworking App</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container">
        <a class="navbar-brand" href="/">Coworking</a>
        <div class="navbar-nav ms-auto">
            {% if current_user.is_authenticated %}
                <a class="nav-link" href="/book">Réserver</a>
                <a class="nav-link" href="/my_bookings">Mes réservations</a>
                {% if current_user.is_manager %}
                    <a class="nav-link" href="/manage_rooms">Gérer les salles</a>
                    <a class="nav-link" href="/manage_bookings">Gérer réservations</a>
                {% endif %}
                <a class="nav-link" href="/logout">Déconnexion</a>
            {% else %}
                <a class="nav-link" href="/login">Connexion</a>
                <a class="nav-link" href="/register">Inscription</a>
            {% endif %}
        </div>
    </div>
</nav>
<div class="container mt-4">
    {% with messages = get_flashed_messages() %}
        {% if messages %}
            {% for message in messages %}
                <div class="alert alert-info">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
</div>
</body>
</html>
```

---

## 📄 Exemples de templates (`index.html`, `book_room.html`, etc.)

👉 **Vous pouvez les créer à partir de `base.html`** en héritant avec `{% extends "base.html" %}` et en remplaçant `{% block content %}`.

---

## ✅ `static/style.css` *(optionnel)*

```css
body { padding-top: 20px; }
```

---

## 🧪 Lancer l’application

1. Installez les dépendances :
```bash
pip install -r requirements.txt
```

2. Lancez l'application :
```bash
python app.py
```

3. Accédez à [http://localhost:5000](http://localhost:5000)

---

## 🔐 Compte par défaut

- **Gérant** : `manager` / `password`

---

Souhaitez-vous que je génère aussi tous les templates HTML en ZIP ?