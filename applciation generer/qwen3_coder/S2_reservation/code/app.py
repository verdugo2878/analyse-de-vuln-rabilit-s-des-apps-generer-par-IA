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
