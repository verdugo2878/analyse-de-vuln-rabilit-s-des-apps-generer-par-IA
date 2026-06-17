from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[
        DataRequired(message="Le nom d'utilisateur est requis"),
        Length(min=3, max=80, message="Le nom d'utilisateur doit contenir entre 3 et 80 caractères")
    ])
    email = StringField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Veuillez entrer un email valide")
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message="Le mot de passe est requis"),
        Length(min=6, message="Le mot de passe doit contenir au moins 6 caractères")
    ])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(message="Veuillez confirmer votre mot de passe"),
        EqualTo('password', message="Les mots de passe ne correspondent pas")
    ])
    full_name = StringField('Nom complet', validators=[
        Length(max=100, message="Le nom complet ne peut pas dépasser 100 caractères")
    ])
    submit = SubmitField('S\'inscrire')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris. Veuillez en choisir un autre.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Cet email est déjà utilisé. Veuillez en choisir un autre.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Veuillez entrer un email valide")
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message="Le mot de passe est requis")
    ])
    remember = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

class ProfileForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[
        DataRequired(message="Le nom d'utilisateur est requis"),
        Length(min=3, max=80, message="Le nom d'utilisateur doit contenir entre 3 et 80 caractères")
    ])
    email = StringField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Veuillez entrer un email valide")
    ])
    full_name = StringField('Nom complet', validators=[
        Length(max=100, message="Le nom complet ne peut pas dépasser 100 caractères")
    ])
    bio = TextAreaField('Bio', validators=[
        Length(max=500, message="La bio ne peut pas dépasser 500 caractères")
    ])
    profile_picture = FileField('Photo de profil', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Seules les images sont autorisées (jpg, jpeg, png, gif)')
    ])
    submit = SubmitField('Mettre à jour')
    
    def validate_username(self, username):
        # Vérifier si le nom d'utilisateur est déjà pris par un autre utilisateur
        user = User.query.filter_by(username=username.data).first()
        if user and user.id != self._user_id:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris. Veuillez en choisir un autre.')
    
    def validate_email(self, email):
        # Vérifier si l'email est déjà utilisé par un autre utilisateur
        user = User.query.filter_by(email=email.data).first()
        if user and user.id != self._user_id:
            raise ValidationError('Cet email est déjà utilisé. Veuillez en choisir un autre.')

class AdminUserForm(FlaskForm):
    role = SelectField('Rôle', choices=[
        ('user', 'Utilisateur'),
        ('admin', 'Administrateur')
    ])
    is_active = BooleanField('Compte actif')
    submit = SubmitField('Mettre à jour')
