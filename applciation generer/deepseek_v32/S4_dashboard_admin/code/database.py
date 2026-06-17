from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Employe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telephone = db.Column(db.String(20))
    poste = db.Column(db.String(100))
    date_embauche = db.Column(db.Date, nullable=False)
    salaire = db.Column(db.Float)
    actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telephone = db.Column(db.String(20))
    entreprise = db.Column(db.String(100))
    date_inscription = db.Column(db.DateTime, default=datetime.utcnow)

class Vente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    date_vente = db.Column(db.DateTime, default=datetime.utcnow)
    produit = db.Column(db.String(200))
    statut = db.Column(db.String(50), default='completé')

class Fichier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    chemin = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50))
    taille = db.Column(db.Integer)
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

def init_db():
    """Initialise la base de données avec un utilisateur admin par défaut"""
    db.create_all()
    
    # Créer un utilisateur admin par défaut si aucun n'existe
    if not User.query.filter_by(username='admin').first():
        from werkzeug.security import generate_password_hash
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        
        # Ajouter des données de démo
        from datetime import date
        
        # Clients de démo
        clients = [
            Client(nom="Dupont", email="dupont@exemple.com", telephone="0123456789", entreprise="Entreprise A"),
            Client(nom="Martin", email="martin@exemple.com", telephone="0234567890", entreprise="Entreprise B"),
            Client(nom="Bernard", email="bernard@exemple.com", telephone="0345678901", entreprise="Entreprise C"),
        ]
        
        for client in clients:
            db.session.add(client)
        
        # Employés de démo
        employes = [
            Employe(nom="Lefevre", prenom="Pierre", email="pierre@entreprise.com", 
                   telephone="0456789012", poste="Directeur", 
                   date_embauche=date(2020, 1, 15), salaire=45000),
            Employe(nom="Dubois", prenom="Marie", email="marie@entreprise.com", 
                   telephone="0567890123", poste="Commerciale", 
                   date_embauche=date(2021, 3, 10), salaire=35000),
        ]
        
        for employe in employes:
            db.session.add(employe)
        
        # Ventes de démo
        from datetime import datetime, timedelta
        for i in range(10):
            vente = Vente(
                client_id=(i % 3) + 1,
                montant=1000 + (i * 500),
                produit=f"Produit {i+1}",
                date_vente=datetime.now() - timedelta(days=i*3)
            )
            db.session.add(vente)
        
        db.session.commit()
        print("Base de données initialisée avec succès!")
