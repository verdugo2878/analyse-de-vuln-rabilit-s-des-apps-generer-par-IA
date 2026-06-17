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
