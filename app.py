from flask import Flask, abort, render_template, request, redirect, send_file, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from datetime import datetime, timedelta
from flask_mail import Mail, Message 
from dotenv import load_dotenv 
from flask import jsonify
from sqlalchemy import or_
import random
import string
import os
from flask import make_response
from xhtml2pdf import pisa
from io import BytesIO
from flask import render_template_string
from sqlalchemy import func, extract
from weasyprint import HTML
import calendar
import locale
import sys
try:
    if sys.platform.startswith('win'):  # Windows
        locale.setlocale(locale.LC_TIME, 'French_France.1252')
    else:  # Linux (Render)
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    # Si la locale n'est pas dispo, on laisse la valeur par défaut
    print("⚠️ Locale non disponible, utilisation de la locale par défaut.")


load_dotenv()

app = Flask(__name__)

# Configuration de la base de données PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL") or "postgresql://postgres:touba202@localhost:5432/gestion_stock?sslmode=require"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY") or "une_cle_secrete_tres_forte_et_unique"


# Configuration pour Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'geytoris.stock@gmail.com'
app.config['MAIL_PASSWORD'] = 'dtqa qczc dxaq lslg'
app.config['MAIL_DEFAULT_SENDER'] = 'geytoris.stock@gmail.com'
mail = Mail(app)

# Initialisation des extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def generer_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def generer_reference_recu():
    import uuid
    return f"RC-{uuid.uuid4().hex[:10].upper()}"


class Utilisateur(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nom_utilisateur = db.Column(db.String(80), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100))
    role = db.Column(db.String(20), nullable=False, default='utilisateur')
    nom_boutique = db.Column(db.String(100))
    adresse_boutique = db.Column(db.String(200))
    telephone_boutique = db.Column(db.String(50))
    logo = db.Column(db.String(200))  # Chemin du fichier image/logo

    code_pin = db.Column(db.String(10), nullable=True)

    # Pour la confirmation de compte
    code_confirmation = db.Column(db.String(6))
    code_envoye_a = db.Column(db.DateTime, default=datetime.utcnow)

    # Pour le mot de passe oublié
    code_reset = db.Column(db.String(6))
    reset_envoye_a = db.Column(db.DateTime)



# Modèle Produit
class Produit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.String(300), nullable=True)
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    supprime = db.Column(db.Boolean, default=False)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseur.id'))
    prix_achat = db.Column(db.Float, nullable=False, default=0)
    prix_vente = db.Column(db.Float, nullable=False, default=0)

    
# Modèle Vente
class Vente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produit.id'))
    quantite = db.Column(db.Integer)
    prix_unitaire = db.Column(db.Float)  # ✅ Ajouté ici
    date_vente = db.Column(db.DateTime, default=datetime.utcnow)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'))
    recu_id = db.Column(db.Integer, db.ForeignKey('recu.id'))


# Modèle demande d'inscription
class DemandeInscription(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nom_utilisateur = db.Column(db.String(80), nullable=False)
    mot_de_passe = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100))
    role = db.Column(db.String(20), default='utilisateur')
    code_confirmation = db.Column(db.String(6), nullable=False)
    code_envoye_a = db.Column(db.DateTime, default=datetime.utcnow)
    date_demande = db.Column(db.DateTime, default=datetime.utcnow)
    valide = db.Column(db.Boolean, default=False)

# Modèle Recu 
class Recu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    montant_total = db.Column(db.Float, nullable=False)
    supprime = db.Column(db.Boolean, default=False)  # ✅ Corbeille
    nom_client = db.Column(db.String(100), nullable=True)
    telephone_client = db.Column(db.String(20), nullable=True)
    montant_paye = db.Column(db.Float, default=0)
    monnaie_rendue = db.Column(db.Float, default=0)
    mode_paiement = db.Column(db.String(50), nullable=True)  # ✅ Nouveau champ
    dette = db.relationship('Dette', backref='recu', uselist=False)

    utilisateur = db.relationship('Utilisateur', backref=db.backref('recus', lazy=True))


# Modèle Ligne de vente
class LigneVente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recu_id = db.Column(db.Integer, db.ForeignKey('recu.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produit.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=False)

    produit = db.relationship('Produit')
    recu = db.relationship('Recu', backref=db.backref('lignes', lazy=True, cascade='all, delete'))

# Modèle retour
class Retour(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produit.id'), nullable=False)
    recu_id = db.Column(db.Integer, db.ForeignKey('recu.id'), nullable=False)  # au lieu de vente_id
    quantite_retournee = db.Column(db.Integer, nullable=False)
    motif = db.Column(db.Text)
    date_retour = db.Column(db.DateTime, default=datetime.utcnow)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'))
    supprime = db.Column(db.Boolean, default=False)
    produit = db.relationship('Produit')
    recu = db.relationship('Recu', backref=db.backref('retours', lazy=True, cascade="all, delete-orphan"))


class StatistiqueMensuelle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey("utilisateur.id"), nullable=False)
    mois = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    chiffre_affaires = db.Column(db.Float, default=0.0)
    nombre_ventes = db.Column(db.Integer, default=0)
    date_enregistrement = db.Column(db.DateTime, default=datetime.utcnow)

class Fournisseur(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    adresse = db.Column(db.Text)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    supprime = db.Column(db.Boolean, default=False)
    produits = db.relationship('Produit', backref='fournisseur', lazy=True)

    def __repr__(self):
        return f'<Fournisseur {self.nom}'   

class Dette(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_nom = db.Column(db.String(100), nullable=False)
    client_telephone = db.Column(db.String(20))
    montant_total = db.Column(db.Float, nullable=False)
    montant_rembourse = db.Column(db.Float, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_remboursement = db.Column(db.DateTime, nullable=True)
    
    recu_id = db.Column(db.Integer, db.ForeignKey('recu.id'))  # Lien vers le reçu
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'))

    supprime = db.Column(db.Boolean, default=False)  # Pour une future corbeille

    @property
    def reste_a_payer(self):
        return round(self.montant_total - self.montant_rembourse, 2)

    def est_reglee(self):
        return self.reste_a_payer <= 0



class Remboursement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    montant = db.Column(db.Float, nullable=False)
    date_remboursement = db.Column(db.DateTime, default=datetime.utcnow)

    dette_id = db.Column(db.Integer, db.ForeignKey('dette.id'), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)

    dette = db.relationship('Dette', backref=db.backref('remboursements', lazy=True))

  

class ArchiveStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    mois = db.Column(db.String(20), nullable=False)  # ex: "Juillet 2025"
    chiffre_affaires = db.Column(db.Float, nullable=False, default=0)
    total_achats = db.Column(db.Float, nullable=False, default=0)
    benefice = db.Column(db.Float, nullable=False, default=0)
    marge = db.Column(db.Float, nullable=False, default=0)
    nb_ventes = db.Column(db.Integer, nullable=False, default=0)
    date_enregistrement = db.Column(db.DateTime, default=datetime.utcnow)



# Chargement utilisateur
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Utilisateur, int(user_id))

# Route principale
@app.route('/')
@login_required
def index():
    recherche = request.args.get('recherche', '').strip().lower()

    # Base : produits non supprimés de l'utilisateur
    requete = Produit.query.filter_by(utilisateur_id=current_user.id, supprime=False)

    # Appliquer le filtre de recherche si présent
    if recherche:
        requete = requete.filter(
            Produit.nom.ilike(f'%{recherche}%') | Produit.description.ilike(f'%{recherche}%')
        )

    produits = requete.all()

    produits_rupture = Produit.query.filter_by(utilisateur_id=current_user.id, quantite=0, supprime=False).all()
    fournisseurs = Fournisseur.query.filter_by(utilisateur_id=current_user.id, supprime=False).all()
    
    fournisseur_id_selectionne = request.args.get('fournisseur_id')

    return render_template(
        'index.html',
        stock=produits,
        ruptures=produits_rupture,
        fournisseurs=fournisseurs,
        fournisseur_id_selectionne=fournisseur_id_selectionne
    )


# Route pour ajouter un produit
@app.route('/ajouter', methods=['POST'])
@login_required
def ajouter():
    nom = request.form.get('nom')
    description = request.form.get('description')
    quantite = int(request.form.get('quantite'))
    prix_achat = float(request.form.get('prix_achat'))
    prix_vente = float(request.form.get('prix_vente'))
    fournisseur_id = request.form.get('fournisseur_id')

    produit = Produit(
        nom=nom,
        description=description,
        quantite=quantite,
        prix_achat=prix_achat,
        prix_vente=prix_vente,
        fournisseur_id=fournisseur_id,
        utilisateur_id=current_user.id
    )
    db.session.add(produit)
    db.session.commit()
    flash("✅ Produit ajouté avec succès.", "success")
    return redirect(url_for('index'))



# Route pour supprimer un produit
@app.route('/supprimer_vente/<int:id>', methods=['POST'])
@login_required
def supprimer_vente(id):
    vente = Vente.query.get_or_404(id)
    if vente.utilisateur_id != current_user.id:
        abort(403)

    vente.supprime = True
    db.session.commit()

    msg = Message(
        subject="Vente supprimée",
        recipients=[current_user.email],
        body=f"La vente du produit '{vente.produit.nom}' (quantité : {vente.quantite}) a été supprimée."
    )
    mail.send(msg)

    flash("Vente supprimée avec succès.", "success")
    return redirect(url_for('historique'))



@app.route('/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_produit(id):
    produit = Produit.query.get_or_404(id)

    # ✅ Vérification de l’utilisateur
    if produit.utilisateur_id != current_user.id:
        abort(403)

    # ✅ Valeurs avant modification
    ancien = {
        "nom": produit.nom,
        "description": produit.description,
        "quantite": produit.quantite,
        "prix_achat": produit.prix_achat,
        "prix_vente": produit.prix_vente,
    }

    if request.method == 'POST':
        # ✅ Récupération des nouvelles valeurs
        nouveau_nom = request.form['nom']
        nouvelle_description = request.form['description']
        nouvelle_quantite = int(request.form['quantite'])

        # On remplace la virgule par un point si besoin
        prix_achat_str = request.form['prix_achat'].replace(',', '.')
        prix_vente_str = request.form['prix_vente'].replace(',', '.')
        nouveau_prix_achat = float(prix_achat_str)
        nouveau_prix_vente = float(prix_vente_str)

        # ✅ Détection des changements
        modifications = []
        if ancien["nom"] != nouveau_nom:
            modifications.append(f'Nom : "{ancien["nom"]}" → "{nouveau_nom}"')
        if ancien["description"] != nouvelle_description:
            modifications.append(f'Description : "{ancien["description"]}" → "{nouvelle_description}"')
        if ancien["quantite"] != nouvelle_quantite:
            modifications.append(f'Quantité : {ancien["quantite"]} → {nouvelle_quantite}')
        if ancien["prix_achat"] != nouveau_prix_achat:
            modifications.append(f'Prix d\'achat : {ancien["prix_achat"]} → {nouveau_prix_achat}')
        if ancien["prix_vente"] != nouveau_prix_vente:
            modifications.append(f'Prix de vente : {ancien["prix_vente"]} → {nouveau_prix_vente}')

        # ✅ Si aucune modification
        if not modifications:
            flash("Aucune modification détectée.", "info")
            return redirect(url_for('index'))

        # ✅ Appliquer les modifications
        produit.nom = nouveau_nom
        produit.description = nouvelle_description
        produit.quantite = nouvelle_quantite
        produit.prix_achat = nouveau_prix_achat
        produit.prix_vente = nouveau_prix_vente
        db.session.commit()

        # ✅ Message récapitulatif
        message = (
            f'Le produit "{ancien["nom"]}" a été modifié avec les changements suivants : '
            + "; ".join(modifications) + "."
        )

        # ✅ Envoi d’un mail de notification (si email dispo)
        if current_user.email:
            try:
                msg = Message(
                    subject="Modification de produit",
                    recipients=[current_user.email],
                    body=message
                )
                mail.send(msg)
            except Exception as e:
                print("Erreur lors de l'envoi du mail :", e)
                flash("Erreur lors de l'envoi de l'e-mail de notification.", "warning")

        flash("✅ Produit modifié avec succès.", "success")
        return redirect(url_for('index'))

    return render_template('modifier.html', produit=produit)



# Routes de connexion / déconnexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        nom = request.form['nom_utilisateur']
        mot_de_passe = request.form['mot_de_passe']
        utilisateur = Utilisateur.query.filter_by(nom_utilisateur=nom).first()
        if utilisateur and check_password_hash(utilisateur.mot_de_passe, mot_de_passe):
            login_user(utilisateur)
            flash("Connexion réussie.", "success")
            return redirect(url_for('index'))
        flash("Identifiants invalides.", "danger")
    return render_template('login.html',app_name='Geytoris')


@app.route('/demande_inscription', methods=['POST'])
def demande_inscription():
    nom = request.form['nom_utilisateur']
    email = request.form['email']
    mot_de_passe = request.form['mot_de_passe']
    code = generer_code()

    mot_de_passe_hash = generate_password_hash(mot_de_passe)
    demande = DemandeInscription(
        nom_utilisateur=nom,
        email=email,
        mot_de_passe=mot_de_passe_hash,
        code_confirmation=code,
        code_envoye_a=datetime.utcnow() 
    )
    db.session.add(demande)
    db.session.commit()

    try:
        # Envoi du mail à toi
        msg = Message("Nouvelle demande d'inscription",
                      recipients=["gkhadim202@gmail.com"])
        msg.body = f"Demande d'inscription de :\nNom : {nom}\nEmail : {email}\nCode : {code}"
        mail.send(msg)
    except Exception as e:
        print("⚠️ Erreur lors de l'envoi du mail :", e)
        flash("Une erreur est survenue lors de l'envoi du mail de validation. Contactez l'administrateur.", "danger")
        return redirect(url_for('login'))

    flash("Demande envoyée avec succès. Veuillez entrer le code de validation.", "success")
    return redirect(url_for('valider_code_utilisateur', demande_id=demande.id))


@app.route('/valider_code/<int:demande_id>', methods=['GET', 'POST'])
def valider_code_utilisateur(demande_id):
    demande = DemandeInscription.query.get_or_404(demande_id)

    # Vérifier si le code est expiré (10 minutes)
    delai_expiration = timedelta(minutes=10)
    maintenant = datetime.utcnow()
    if demande.code_envoye_a and maintenant - demande.code_envoye_a > delai_expiration:
        flash("⏳ Le code de confirmation a expiré. Veuillez faire une nouvelle demande.", "warning")
        return redirect(url_for('register'))

    if request.method == 'POST':
        code_saisi = request.form['code']
        if code_saisi == demande.code_confirmation:
            utilisateur = Utilisateur(
                nom_utilisateur=demande.nom_utilisateur,
                mot_de_passe=demande.mot_de_passe,
                email=demande.email,
                role=demande.role
            )
            db.session.add(utilisateur)
            demande.valide = True
            db.session.commit()

            flash("Compte validé avec succès. Vous pouvez maintenant vous connecter.", "success")
            return redirect(url_for('login'))
        else:
            flash("Code incorrect. Veuillez réessayer.", "danger")

    return render_template('code_confirmation.html', demande=demande)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Déconnecté avec succès.", "success")
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom_utilisateur = request.form.get('nom_utilisateur')
        email = request.form.get('email')
        mot_de_passe = request.form.get('mot_de_passe')
        password = request.form['password']
        confirm_password = request.form['confirm_password'] 

        if not nom_utilisateur or not email or not mot_de_passe:
            flash("Tous les champs sont obligatoires.", "danger")
            return redirect(url_for('register'))

        if Utilisateur.query.filter_by(nom_utilisateur=nom_utilisateur).first():
            flash("Ce nom d'utilisateur existe déjà.", "warning")
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for('register'))

        hash_pw = generate_password_hash(mot_de_passe)
        nouvel_utilisateur = Utilisateur(
            nom_utilisateur=nom_utilisateur,
            mot_de_passe=hash_pw,
            email=email,
            role='utilisateur'  # ✅ Ajouter cette ligne
        )
        db.session.add(nouvel_utilisateur)
        db.session.commit()
        flash("Inscription réussie. Vous pouvez vous connecter.", "success")
        return redirect(url_for('login'))

    return render_template('register.html',app_name='Geytoris') 


@app.route('/admin/utilisateurs')
def liste_utilisateurs():
    utilisateurs = Utilisateur.query.all()
    return render_template('admin_utilisateurs.html', utilisateurs=utilisateurs)


@app.route('/corbeille')
@login_required
def corbeille():
    produits_supprimes = Produit.query.filter_by(utilisateur_id=current_user.id, supprime=True).all()
    return render_template('corbeille.html', produits=produits_supprimes)


@app.route('/corbeille_ventes')
@login_required
def corbeille_ventes():
    ventes_supprimees = Vente.query.filter_by(utilisateur_id=current_user.id, supprime=True).all()
    return render_template('corbeille_ventes.html', ventes=ventes_supprimees)


@app.route('/restaurer_produit/<int:id>', methods=['POST'])
@login_required
def restaurer_produit(id):
    produit = Produit.query.get_or_404(id)
    if produit.utilisateur_id != current_user.id:
        abort(403)
    produit.supprime = False
    db.session.commit()
    flash("Produit restauré avec succès.", "success")
    return redirect(url_for('corbeille'))


@app.route('/restaurer_vente/<int:id>', methods=['POST'])
@login_required
def restaurer_vente(id):
    vente = Vente.query.get_or_404(id)
    if vente.utilisateur_id != current_user.id:
        abort(403)
    vente.supprime = False
    db.session.commit()
    flash("Vente restaurée avec succès.", "success")
    return redirect(url_for('corbeille_ventes'))


@app.route('/supprimer_definitif_produit/<int:id>', methods=['POST'])
@login_required
def supprimer_definitif_produit(id):
    produit = Produit.query.get_or_404(id)
    if produit.utilisateur_id != current_user.id:
        abort(403)
    db.session.delete(produit)
    db.session.commit()
    flash("Produit supprimé définitivement.", "success")
    return redirect(url_for('corbeille'))


@app.route('/supprimer_definitif_vente/<int:id>', methods=['POST'])
@login_required
def supprimer_definitif_vente(id):
    vente = Vente.query.get_or_404(id)
    if vente.utilisateur_id != current_user.id:
        abort(403)
    vente.supprime = True
    db.session.commit()
    flash("Vente supprimée définitivement.", "success")
    return redirect(url_for('corbeille_ventes'))


@app.route('/supprimer_produit/<int:id>', methods=['POST'])
@login_required
def supprimer_produit(id):
    produit = Produit.query.get_or_404(id)
    if produit.utilisateur_id != current_user.id:
        abort(403)

    produit.supprime = True
    db.session.commit()

    # Envoi du mail avec message personnalisé
    if current_user.email:
        msg = Message(
            subject="Produit supprimé",
            recipients=[current_user.email],
            body=f"Produit ({produit.nom}) est supprimé."
        )
        mail.send(msg)

    flash("Produit déplacé dans la corbeille avec succès.", "success")
    return redirect(url_for('index'))


@app.route('/mot_de_passe_oublie', methods=['GET', 'POST'])
def mot_de_passe_oublie():
    if request.method == 'POST':
        email = request.form.get('email')
        utilisateur = Utilisateur.query.filter_by(email=email).first()

        if utilisateur:
            code = generer_code()
            utilisateur.code_reset = code
            utilisateur.reset_envoye_a = datetime.utcnow()
            db.session.commit()

            msg = Message(
                subject="Code de réinitialisation de mot de passe",
                recipients=[email],
                body=f"Votre code de réinitialisation est : {code}.\nIl est valable 10 minutes."
            )
            mail.send(msg)
            flash("Un code vous a été envoyé par e-mail.", "info")
            return redirect(url_for('confirmer_code_reset', user_id=utilisateur.id))
        else:
            flash("Aucun compte trouvé avec cet e-mail.", "warning")

    return render_template('mot_de_passe_oublie.html')


@app.route('/confirmer_code_reset/<int:user_id>', methods=['GET', 'POST'])
def confirmer_code_reset(user_id):
    utilisateur = Utilisateur.query.get_or_404(user_id)
    expiration = timedelta(minutes=10)

    # Vérifier si le code a expiré
    if datetime.utcnow() - utilisateur.reset_envoye_a > expiration:
        flash("⏳ Le code a expiré. Veuillez refaire une demande.", "warning")
        return redirect(url_for('mot_de_passe_oublie'))

    # Vérification du code saisi
    if request.method == 'POST':
        code_saisi = request.form.get('code')
        if code_saisi == utilisateur.code_reset:
            return redirect(url_for('creer_nouveau_mot_de_passe', user_id=user_id))
        else:
            flash("Code incorrect. Veuillez réessayer.", "danger")

    # 🟡 Calcul du temps restant
    temps_restant = max(0, int((utilisateur.reset_envoye_a + expiration - datetime.utcnow()).total_seconds()))

    # ✅ Envoi du temps restant au template
    return render_template('confirmer_code_reset.html', utilisateur=utilisateur, temps_restant=temps_restant)



@app.route('/nouveau_mot_de_passe/<int:user_id>', methods=['GET', 'POST'])
def creer_nouveau_mot_de_passe(user_id):
    utilisateur = Utilisateur.query.get_or_404(user_id)

    if request.method == 'POST':
        mot_de_passe = request.form.get('mot_de_passe')
        if mot_de_passe:
            utilisateur.mot_de_passe = generate_password_hash(mot_de_passe)
            utilisateur.code_reset = None
            utilisateur.reset_envoye_a = None
            db.session.commit()
            flash("Mot de passe mis à jour. Vous pouvez vous connecter.", "success")
            return redirect(url_for('login'))

    return render_template('nouveau_mot_de_passe.html')


@app.route('/renvoyer_code_reset/<int:user_id>', methods=['POST'])
def renvoyer_code_reset(user_id):
    utilisateur = Utilisateur.query.get_or_404(user_id)
    if utilisateur.reset_envoye_a and datetime.utcnow() - utilisateur.reset_envoye_a < timedelta(seconds=60):
        flash("⏳ Veuillez attendre une minute avant de demander un nouveau code.", "warning")
        return redirect(url_for('confirmer_code_reset', user_id=user_id))

    nouveau_code = generer_code()
    utilisateur.code_reset = nouveau_code
    utilisateur.reset_envoye_a = datetime.utcnow()
    db.session.commit()

    try:
        msg = Message(
            subject="Nouveau code de réinitialisation",
            recipients=[utilisateur.email],
            body=f"Voici votre nouveau code : {nouveau_code}\nIl est valable 10 minutes."
        )
        mail.send(msg)
        flash("📨 Nouveau code envoyé avec succès.", "success")
    except Exception as e:
        print("Erreur lors de l'envoi :", e)
        flash("Erreur lors de l’envoi du code.", "danger")

    return redirect(url_for('confirmer_code_reset', user_id=user_id))

@app.route("/effectuer_vente", methods=["GET", "POST"])
@login_required
def effectuer_vente():
    # 🔹 Récupérer tous les produits disponibles pour l'utilisateur connecté
    produits = Produit.query.filter_by(utilisateur_id=current_user.id, supprime=False).all()

    if request.method == "POST":
        ventes = []
        montant_total = 0.0

        # 🔹 Infos client
        nom_client = request.form.get("nom_client") or "Client"
        telephone_client = request.form.get("telephone_client") or ""
        try:
            montant_paye = float(request.form.get("montant_paye") or 0)
        except ValueError:
            montant_paye = 0.0

        # 🔹 Récupération du mode de paiement
        mode_paiement = request.form.get("mode_paiement")

        # ✅ Analyse des produits vendus
        for produit in produits:
            qte_str = request.form.get(f"quantite_{produit.id}")
            if qte_str and qte_str.isdigit():
                quantite = int(qte_str)
                if 0 < quantite <= produit.quantite:
                    produit.quantite -= quantite
                    montant = quantite * (produit.prix_vente or 0)
                    montant_total += montant
                    ventes.append((produit.id, quantite, produit.prix_vente))

        # ❌ Aucun produit sélectionné
        if not ventes:
            flash("⚠️ Aucun produit sélectionné pour la vente.", "warning")
            return redirect(url_for("effectuer_vente"))

        # ✅ Création du reçu
        reference = generer_reference_recu()
        recu = Recu(
            reference=reference,
            utilisateur_id=current_user.id,
            montant_total=montant_total,
            montant_paye=montant_paye,
            monnaie_rendue=max(0, montant_paye - montant_total),
            nom_client=nom_client,
            telephone_client=telephone_client,
            mode_paiement=mode_paiement  # 🔹 Ajout du mode de paiement
        )
        db.session.add(recu)
        db.session.flush()  # Permet d’obtenir recu.id avant commit

        # ✅ Enregistrement des lignes de vente
        for prod_id, quantite, prix_unitaire in ventes:
            ligne = LigneVente(
                recu_id=recu.id,
                produit_id=prod_id,
                quantite=quantite,
                prix_unitaire=prix_unitaire
            )
            db.session.add(ligne)

        # ✅ Si paiement partiel → enregistrement d’une dette
        if montant_paye < montant_total:
            nouvelle_dette = Dette(
                client_nom=nom_client,
                client_telephone=telephone_client,
                montant_total=montant_total,
                montant_rembourse=montant_paye,
                recu_id=recu.id,
                utilisateur_id=current_user.id
            )
            db.session.add(nouvelle_dette)

        # ✅ Validation en base
        db.session.commit()
        flash(f"✅ Vente enregistrée avec reçu #{recu.reference}.", "success")

        # 🔹 Rediriger vers la page du reçu
        return redirect(url_for("voir_recu", recu_id=recu.id))

    # Si méthode GET → Afficher la page
    return render_template("effectuer_vente.html", produits=produits)



@app.route('/voir_recu/<int:recu_id>')
@login_required
def voir_recu(recu_id):
    recu = Recu.query.get_or_404(recu_id)
    if recu.utilisateur_id != current_user.id:
        abort(403)
    lignes = LigneVente.query.filter_by(recu_id=recu.id).all()
    return render_template('voir_recu.html', recu=recu, lignes=lignes)



from sqlalchemy import or_

@app.route('/recus')
@login_required
def recus():
    query = request.args.get('q', '').strip().lower()

    if query:
        recus = Recu.query.filter(
            Recu.supprime == False,
            Recu.utilisateur_id == current_user.id,
            or_(
                Recu.nom_client.ilike(f"%{query}%"),
                Recu.reference.ilike(f"%{query}%"),
                Recu.lignes.any(LigneVente.produit.has(Produit.nom.ilike(f"%{query}%")))
            )
        ).order_by(Recu.date_creation.desc()).all()
    else:
        recus = Recu.query.filter_by(utilisateur_id=current_user.id, supprime=False) \
                          .order_by(Recu.date_creation.desc()).all()

    # 👉 Si requête AJAX (fetch), on retourne les reçus au format JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        result = []
        for recu in recus:
            result.append({
                'id': recu.id,
                'reference': recu.reference,
                'date': recu.date_creation.strftime('%d/%m/%Y %H:%M'),
                'montant': recu.montant_total,
                'nom_client': recu.nom_client or 'Non renseigné',
                'tel_client': recu.telephone_client or '',
            })
        return jsonify(result)

    return render_template('recus.html', recus=recus)



@app.route("/recu_pdf/<int:recu_id>")
@login_required
def recu_pdf(recu_id):
    recu = Recu.query.get_or_404(recu_id)

    if recu.utilisateur_id != current_user.id:
        abort(403)

    lignes = LigneVente.query.filter_by(recu_id=recu.id).all()
    utilisateur = current_user

    # ✅ Transmettre la variable utilisateur au template
    html = render_template("recu_pdf.html", recu=recu, lignes=lignes, utilisateur=utilisateur)

    result = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)

    if pisa_status.err:
        flash("Erreur lors de la génération du PDF.", "danger")
        return redirect(url_for("recus"))

    result.seek(0)
    return send_file(result, download_name=f"recu_{recu.reference}.pdf", as_attachment=True)



@app.route('/supprimer_recu/<int:recu_id>', methods=['POST'])
@login_required
def supprimer_recu(recu_id):
    recu = Recu.query.get_or_404(recu_id)

    if recu.utilisateur_id != current_user.id:
        abort(403)

    recu.supprime = True  # suppression logique
    db.session.commit()

    # 🔐 Envoi du mail de notification
    if current_user.email:
        try:
            msg = Message(
                subject="Suppression d’un reçu",
                recipients=[current_user.email],
                body=(
                    f"Bonjour {current_user.nom_utilisateur},\n\n"
                    f"Le reçu avec la référence {recu.reference} a été supprimé (déplacé dans la corbeille) le "
                    f"{recu.date_creation.strftime('%d/%m/%Y à %H:%M:%S')}.\n\n"
                    "Si ce n'était pas vous, veuillez contacter immédiatement l’administrateur.\n\n"
                    "Ceci est un message automatique de sécurité."
                )
            )
            mail.send(msg)
        except Exception as e:
            print("❌ Erreur envoi email suppression reçu :", e)
            flash("⚠️ Erreur lors de l'envoi de l'e-mail de notification.", "warning")

    flash("Reçu déplacé dans la corbeille.", "success")
    return redirect(url_for('recus'))


@app.route('/corbeille_recus')
@login_required
def corbeille_recus():
    recus = Recu.query.filter_by(utilisateur_id=current_user.id, supprime=True).order_by(Recu.date_creation.desc()).all()
    return render_template('corbeille_recus.html', recus=recus)


@app.route('/restaurer_recu/<int:recu_id>', methods=['POST'])
@login_required
def restaurer_recu(recu_id):
    recu = Recu.query.get_or_404(recu_id)
    if recu.utilisateur_id != current_user.id:
        abort(403)
    recu.supprime = False
    db.session.commit()
    flash("Reçu restauré avec succès.", "success")
    return redirect(url_for('corbeille_recus'))


@app.route('/supprimer_definitif_recu/<int:recu_id>', methods=['POST'])
@login_required
def supprimer_definitif_recu(recu_id):
    recu = Recu.query.get_or_404(recu_id)
    if recu.utilisateur_id != current_user.id:
        abort(403)

    # Supprimer d'abord les lignes de vente associées
    LigneVente.query.filter_by(recu_id=recu.id).delete()
    db.session.delete(recu)
    db.session.commit()
    flash("Reçu supprimé définitivement.", "success")
    return redirect(url_for('corbeille_recus'))


@app.route('/retour/<int:recu_id>', methods=['GET', 'POST'])
@login_required
def effectuer_retour(recu_id):
    recu = Recu.query.get_or_404(recu_id)

    # Vérification d'accès
    if recu.utilisateur_id != current_user.id:
        flash("Accès refusé à ce reçu.", "danger")
        return redirect(url_for('historique'))

    lignes = recu.lignes  # Grâce au backref

    if request.method == 'POST':
        retours_effectues = 0
        for ligne in lignes:
            qte = request.form.get(f'qte_{ligne.produit.id}')
            motif = request.form.get(f'motif_{ligne.produit.id}')
            if qte:
                try:
                    qte = int(qte)
                    if 0 < qte <= ligne.quantite:
                        retour = Retour(
                            produit_id=ligne.produit.id,
                            quantite_retournee=qte,
                            motif=motif.strip() if motif else None,
                            utilisateur_id=current_user.id,
                            recu_id=recu.id  # ou recu_id si tu veux le lier ainsi
                        )
                        db.session.add(retour)
                        ligne.produit.quantite += qte
                        retours_effectues += 1
                except ValueError:
                    continue

        if retours_effectues > 0:
            db.session.commit()
            flash(f"{retours_effectues} retour(s) enregistré(s).", "success")
        else:
            flash("Aucun retour valide détecté.", "warning")
        return redirect(url_for('liste_retours'))

    return render_template("retour_produits.html", recu=recu, lignes=lignes)

@app.route('/retours', endpoint='liste_retours')
@login_required
def retours():
    recherche = request.args.get('recherche', '')
    filtre = request.args.get('filtre', 'tous')
    tri = request.args.get('tri', 'date_desc')

    requete = Retour.query.join(Produit).filter(Retour.utilisateur_id == current_user.id, Retour.supprime == False)

    if recherche:
        requete = requete.filter(Produit.nom.ilike(f"%{recherche}%"))

    if filtre == 'mois':
        from datetime import datetime
        now = datetime.now()
        requete = requete.filter(db.extract('month', Retour.date_retour) == now.month)
    elif filtre == 'aujourdhui':
        from datetime import date
        requete = requete.filter(db.func.date(Retour.date_retour) == date.today())

    # Tri propre sans doublon
    if tri == 'date_asc':
        requete = requete.order_by(Retour.date_retour.asc())
    elif tri == 'produit_asc':
        requete = requete.order_by(Produit.nom.asc())
    elif tri == 'quantite_desc':
        requete = requete.order_by(Retour.quantite_retournee.desc())
    else:
        requete = requete.order_by(Retour.date_retour.desc())

    retours = requete.all()

    return render_template("retours.html", retours=retours, recherche=recherche, filtre=filtre, tri=tri)


@app.route('/supprimer_recu/<int:recu_id>', methods=['POST'])
@login_required
def supprimer_recu_view(recu_id):
    recu = Recu.query.get_or_404(recu_id)

    if recu.utilisateur_id != current_user.id:
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('historique_recus'))

    recu.supprime = True
    db.session.commit()
    flash("Reçu déplacé dans la corbeille.", "success")
    return redirect(url_for('historique_recus'))


@app.route('/corbeille_recus')
@login_required
def voir_corbeille_recus():
    recus = Recu.query.filter_by(utilisateur_id=current_user.id, supprime=True).order_by(Recu.date_creation.desc()).all()
    return render_template('corbeille_recus.html', recus=recus)


@app.route('/restaurer_recu/<int:recu_id>', methods=['POST'])
@login_required
def restaurer_recu_view(recu_id):
    recu = Recu.query.get_or_404(recu_id)
    if recu.utilisateur_id != current_user.id:
        flash("Action non autorisée.", "danger")
    else:
        recu.supprime = False
        db.session.commit()
        flash("Reçu restauré avec succès.", "success")
    return redirect(url_for('corbeille_recus'))

@app.route('/supprimer_recu_definitif/<int:recu_id>', methods=['POST'])
@login_required
def supprimer_recu_definitif(recu_id):
    recu = Recu.query.get_or_404(recu_id)
    if recu.utilisateur_id != current_user.id:
        flash("Action non autorisée.", "danger")
        return redirect(url_for('corbeille_recus'))

    for ligne in recu.lignes_vente:
        for retour in ligne.retours:
            db.session.delete(retour)
        db.session.delete(ligne)

    db.session.delete(recu)
    db.session.commit()
    flash("Reçu supprimé définitivement.", "success")
    return redirect(url_for('corbeille_recus'))


@app.route('/supprimer_retour/<int:retour_id>', methods=['POST'])
@login_required
def supprimer_retour(retour_id):
    retour = Retour.query.get_or_404(retour_id)

    if retour.utilisateur_id != current_user.id:
        flash("Action non autorisée.", "danger")
        return redirect(url_for('liste_retours'))

    retour.supprime = True
    retour.produit.stock -= retour.quantite_retournee  
    db.session.commit()

    flash("Retour déplacé dans la corbeille.", "success")
    return redirect(url_for('liste_retours'))

@app.route('/corbeille_retours')
@login_required
def corbeille_retours():
    retours = Retour.query.filter_by(utilisateur_id=current_user.id, supprime=True).order_by(Retour.date_retour.desc()).all()
    return render_template('corbeille_retours.html', retours=retours)

@app.route('/restaurer_retour/<int:retour_id>', methods=['POST'])
@login_required
def restaurer_retour(retour_id):
    retour = Retour.query.get_or_404(retour_id)
    if retour.utilisateur_id == current_user.id:
        retour.supprime = False
        retour.produit.stock += retour.quantite_retournee
        db.session.commit()
        flash("Retour restauré.", "success")
    return redirect(url_for('corbeille_retours'))

@app.route('/supprimer_retour_definitif/<int:retour_id>', methods=['POST'])
@login_required
def supprimer_retour_definitif(retour_id):
    retour = Retour.query.get_or_404(retour_id)
    if retour.utilisateur_id == current_user.id:
        db.session.delete(retour)
        db.session.commit()
        flash("Retour supprimé définitivement.", "success")
    return redirect(url_for('corbeille_retours'))

@app.route('/stats')
@login_required
def stats():
    utilisateur_id = current_user.id
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    # Produits les plus vendus du mois
    produits_vendus = db.session.query(
        Produit.nom,
        func.sum(LigneVente.quantite).label('total_vendu')
    ).join(Produit, LigneVente.produit_id == Produit.id)\
     .join(Recu, LigneVente.recu_id == Recu.id)\
     .filter(
         Recu.utilisateur_id == utilisateur_id,
         extract('month', Recu.date_creation) == current_month,
         extract('year', Recu.date_creation) == current_year
     )\
     .group_by(Produit.nom)\
     .order_by(func.sum(LigneVente.quantite).desc())\
     .limit(4).all()

    # Stock faible
    stock_faible = Produit.query.filter(
        Produit.utilisateur_id == utilisateur_id,
        Produit.quantite < 2,
        Produit.supprime == False
    ).all()

    # Nombre de ventes
    nb_ventes = db.session.query(func.count(Recu.id))\
        .filter(
            Recu.utilisateur_id == utilisateur_id,
            extract('month', Recu.date_creation) == current_month,
            extract('year', Recu.date_creation) == current_year
        ).scalar() or 0

    # Chiffre d'affaires
    total_ventes = db.session.query(
        func.sum(LigneVente.quantite * LigneVente.prix_unitaire)
    ).join(Recu, LigneVente.recu_id == Recu.id)\
     .filter(
         Recu.utilisateur_id == utilisateur_id,
         extract('month', Recu.date_creation) == current_month,
         extract('year', Recu.date_creation) == current_year
     ).scalar() or 0

    # Coût d’achat total
    prix_achat_total = db.session.query(
        func.sum(LigneVente.quantite * Produit.prix_achat)
    ).join(Produit, LigneVente.produit_id == Produit.id)\
     .join(Recu, LigneVente.recu_id == Recu.id)\
     .filter(
         Recu.utilisateur_id == utilisateur_id,
         extract('month', Recu.date_creation) == current_month,
         extract('year', Recu.date_creation) == current_year
     ).scalar() or 0

    # Bénéfice = ventes - achats
    benefice_total = total_ventes - prix_achat_total

    # Marge = bénéfice / chiffre d’affaires * 100
    marge_pourcentage = 0
    if total_ventes > 0:
        marge_pourcentage = (benefice_total / total_ventes) * 100

    # Nom du mois
    mois_actuel = now.strftime("%B")

    return render_template(
    "stats.html",
    produits_vendus=produits_vendus,
    stock_faible=stock_faible,
    nb_ventes=nb_ventes,
    total_ventes=total_ventes,
    total_achats=prix_achat_total,   # <--- ajoute cet alias
    benefice_total=benefice_total,
    marge_pourcentage=marge_pourcentage,
    mois=mois_actuel
)


@app.route("/rapport_pdf")
@login_required
def rapport_pdf():
    utilisateur_id = current_user.id
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    # Produits les plus vendus
    produits_vendus = db.session.query(
        Produit.nom,
        func.sum(LigneVente.quantite).label('total_vendu')
    ).join(Produit, LigneVente.produit_id == Produit.id)\
     .join(Recu, LigneVente.recu_id == Recu.id)\
     .filter(
         Recu.utilisateur_id == utilisateur_id,
         extract('month', Recu.date_creation) == current_month,
         extract('year', Recu.date_creation) == current_year
     )\
     .group_by(Produit.nom)\
     .order_by(func.sum(LigneVente.quantite).desc())\
     .limit(4).all()

    # Stock faible
    stock_faible = Produit.query.filter(
        Produit.utilisateur_id == utilisateur_id,
        Produit.supprime == False,
        Produit.quantite < 2
    ).all()

    # Nombre de ventes
    nb_ventes = db.session.query(func.count(Recu.id))\
        .filter(
            Recu.utilisateur_id == utilisateur_id,
            extract('month', Recu.date_creation) == current_month,
            extract('year', Recu.date_creation) == current_year
        ).scalar()

    # Chiffre d'affaires
    total_ventes = db.session.query(
        func.sum(LigneVente.quantite * LigneVente.prix_unitaire)
    ).join(Recu, LigneVente.recu_id == Recu.id)\
     .filter(
         Recu.utilisateur_id == utilisateur_id,
         extract('month', Recu.date_creation) == current_month,
         extract('year', Recu.date_creation) == current_year
     ).scalar() or 0

    # Total prix d'achat
    prix_achat_total = db.session.query(
        func.sum(LigneVente.quantite * Produit.prix_achat)
    ).join(Produit, LigneVente.produit_id == Produit.id)\
     .join(Recu, LigneVente.recu_id == Recu.id)\
     .filter(
         Recu.utilisateur_id == utilisateur_id,
         extract('month', Recu.date_creation) == current_month,
         extract('year', Recu.date_creation) == current_year
     ).scalar() or 0

    # Bénéfice
    benefice_total = total_ventes - prix_achat_total

    # Marge %
    marge_pourcentage = 0
    if total_ventes > 0:
        marge_pourcentage = (benefice_total / total_ventes) * 100

    mois_actuel = now.strftime("%B")

    # Passer les nouvelles variables au template
    rendered = render_template(
        "rapport_pdf.html",
        produits_vendus=produits_vendus,
        stock_faible=stock_faible,
        nb_ventes=nb_ventes,
        total_ventes=total_ventes,
        prix_achat_total=prix_achat_total,
        benefice_total=benefice_total,
        marge_pourcentage=marge_pourcentage,
        mois=mois_actuel,
        now=now
    )

    pdf = BytesIO()
    pisa.CreatePDF(BytesIO(rendered.encode("utf-8")), dest=pdf)

    response = make_response(pdf.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=rapport_{mois_actuel}.pdf"
    return response


@app.route("/generer_stats_mensuelles")
@login_required
def generer_stats_mensuelles():
    utilisateur_id = current_user.id
    now = datetime.now()
    mois = now.month - 1 or 12
    annee = now.year if now.month != 1 else now.year - 1

    # Évite de dupliquer
    existe = StatistiqueMensuelle.query.filter_by(utilisateur_id=utilisateur_id, mois=mois, annee=annee).first()
    if existe:
        flash("Les statistiques de ce mois sont déjà enregistrées.", "warning")
        return redirect(url_for("stats"))

    # Données à calculer
    chiffre_affaires = db.session.query(func.sum(LigneVente.quantite * LigneVente.prix_unitaire))\
        .join(Recu).filter(Recu.utilisateur_id == utilisateur_id,
                           extract('month', Recu.date_creation) == mois,
                           extract('year', Recu.date_creation) == annee).scalar() or 0

    nombre_ventes = db.session.query(func.count(Recu.id))\
        .filter(Recu.utilisateur_id == utilisateur_id,
                extract('month', Recu.date_creation) == mois,
                extract('year', Recu.date_creation) == annee).scalar()

    # Enregistrement
    stats = StatistiqueMensuelle(
        utilisateur_id=utilisateur_id,
        mois=mois,
        annee=annee,
        chiffre_affaires=chiffre_affaires,
        nombre_ventes=nombre_ventes
    )
    db.session.add(stats)
    db.session.commit()

    flash("Statistiques du mois précédent enregistrées avec succès.", "success")
    return redirect(url_for("stats"))

@app.route("/historique_stats")
@login_required
def historique_stats():
    stats = StatistiqueMensuelle.query.filter_by(utilisateur_id=current_user.id)\
        .order_by(StatistiqueMensuelle.annee.desc(), StatistiqueMensuelle.mois.desc()).all()

    return render_template("historique_stats.html", stats=stats)

@app.route('/ajouter_fournisseur', methods=['GET', 'POST'])
@login_required
def ajouter_fournisseur():
    if request.method == 'POST':
        nom = request.form['nom']
        telephone = request.form['telephone']
        email = request.form['email']
        adresse = request.form['adresse']
        
        nouveau_fournisseur = Fournisseur(
            nom=nom,
            telephone=telephone,
            email=email,
            adresse=adresse,
            utilisateur_id=current_user.id
        )
        db.session.add(nouveau_fournisseur)
        db.session.commit()

        flash("Fournisseur ajouté avec succès.", "success")
        # Redirection vers la page d'accueil avec l'ID du nouveau fournisseur
        return redirect(url_for('index', fournisseur_id=nouveau_fournisseur.id))

    return render_template('ajouter_fournisseur.html')


@app.route('/fournisseurs')
@login_required
def fournisseurs():
    fournisseurs = Fournisseur.query.filter_by(utilisateur_id=current_user.id, supprime=False).all()
    return render_template('fournisseurs.html', fournisseurs=fournisseurs)


@app.route('/fournisseur/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_fournisseur(id):
    fournisseur = Fournisseur.query.get_or_404(id)
    if fournisseur.utilisateur_id != current_user.id:
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('fournisseurs'))

    if request.method == 'POST':
        fournisseur.nom = request.form['nom']
        fournisseur.telephone = request.form['telephone']
        fournisseur.email = request.form['email']
        fournisseur.adresse = request.form['adresse']
        db.session.commit()
        flash("Fournisseur modifié avec succès.", "success")
        return redirect(url_for('fournisseurs'))

    return render_template('modifier_fournisseur.html', fournisseur=fournisseur)


@app.route('/fournisseur/supprimer/<int:id>', methods=['POST'])
@login_required
def supprimer_fournisseur(id):
    fournisseur = Fournisseur.query.get_or_404(id)
    if fournisseur.utilisateur_id != current_user.id:
        abort(403)
    fournisseur.supprime = True
    db.session.commit()
    flash('Fournisseur déplacé dans la corbeille.', 'warning')
    return redirect(url_for('fournisseurs'))



@app.route('/corbeille_fournisseurs')
@login_required
def corbeille_fournisseurs():
    fournisseurs_supprimes = Fournisseur.query.filter_by(utilisateur_id=current_user.id, supprime=True).all()
    return render_template('corbeille_fournisseurs.html', fournisseurs=fournisseurs_supprimes)


@app.route('/restaurer_fournisseur/<int:id>', methods=['POST'])
@login_required
def restaurer_fournisseur(id):
    fournisseur = Fournisseur.query.get_or_404(id)
    if fournisseur.utilisateur_id != current_user.id:
        abort(403)
    fournisseur.supprime = False
    db.session.commit()
    flash('Fournisseur restauré avec succès.', 'success')
    return redirect(url_for('corbeille_fournisseurs'))


@app.route('/supprimer_fournisseur_definitivement/<int:id>', methods=['POST'])
@login_required
def supprimer_fournisseur_definitivement(id):
    fournisseur = Fournisseur.query.get_or_404(id)
    if fournisseur.utilisateur_id != current_user.id:
        abort(403)
    db.session.delete(fournisseur)
    db.session.commit()
    flash('Fournisseur supprimé définitivement.', 'danger')
    return redirect(url_for('corbeille_fournisseurs'))


@app.route('/rechercher_produits')
@login_required
def rechercher_produits():
    q = request.args.get('q', '').strip().lower()

    # Jointure avec Fournisseur
    produits = Produit.query.join(Fournisseur, isouter=True).filter(
        Produit.utilisateur_id == current_user.id,
        Produit.supprime == False,
        (
            Produit.nom.ilike(f'%{q}%') |
            Produit.description.ilike(f'%{q}%') |
            Fournisseur.nom.ilike(f'%{q}%')
        )
    ).all()

    return render_template('partials/_table_produits.html', stock=produits)


@app.route('/dettes')
@login_required
def dettes():
    dettes = Dette.query.filter_by(utilisateur_id=current_user.id, supprime=False).all()
    return render_template('dettes.html', dettes=dettes)

@app.route('/supprimer_dette/<int:dette_id>', methods=['POST'])
@login_required
def supprimer_dette(dette_id):
    dette = Dette.query.get_or_404(dette_id)
    
    # Sécurité : seule la dette de l'utilisateur courant peut être supprimée
    if dette.utilisateur_id != current_user.id:
        abort(403)

    # Suppression logique (corbeille)
    dette.supprime = True
    db.session.commit()

    # Envoi du mail de notification
    if current_user.email:
        msg = Message(
            subject="Dette supprimée",
            recipients=[current_user.email],
            body=(
                f"La dette du client {dette.client_nom} "
                f"pour un montant de {dette.montant_total:,.0f} FCFA "
                f"a été supprimée et déplacée dans la corbeille."
            )
        )
        mail.send(msg)

    flash("Dette déplacée dans la corbeille avec succès.", "success")
    return redirect(url_for('dettes'))




@app.route('/dettes/<int:dette_id>/rembourser', methods=['GET', 'POST'])
@login_required
def rembourser_dette(dette_id):
    dette = Dette.query.filter_by(id=dette_id, utilisateur_id=current_user.id, supprime=False).first_or_404()

    if request.method == 'POST':
        montant_str = request.form.get('montant')
        try:
            montant = float(montant_str)
        except (ValueError, TypeError):
            flash("Montant invalide.", "danger")
            return redirect(url_for('rembourser_dette', dette_id=dette.id))

        if montant <= 0:
            flash("Le montant doit être supérieur à zéro.", "warning")
            return redirect(url_for('rembourser_dette', dette_id=dette.id))

        restant = dette.montant_total - dette.montant_rembourse

        if montant > restant:
            flash(f"Le montant dépasse le reste à payer ({restant:,.0f} FCFA).", "danger")
            return redirect(url_for('rembourser_dette', dette_id=dette.id))

        # 🔄 Mise à jour du montant remboursé
        dette.montant_rembourse += montant

        # ✅ Si dette soldée → date de remboursement
        if dette.montant_rembourse >= dette.montant_total:
            dette.date_remboursement = datetime.utcnow()

        # 🧾 Enregistrement dans l'historique des remboursements
        remboursement = Remboursement(
            montant=montant,
            dette_id=dette.id,
            utilisateur_id=current_user.id
        )
        db.session.add(remboursement)

        db.session.commit()
        flash("Remboursement enregistré avec succès.", "success")
        return redirect(url_for('dettes'))

    return render_template('rembourser_dette.html', dette=dette)

@app.route('/remboursement/<int:remboursement_id>/recu_pdf')
@login_required
def remboursement_pdf(remboursement_id):
    remboursement = Remboursement.query.get_or_404(remboursement_id)
    dette = remboursement.dette

    if dette.utilisateur_id != current_user.id:
        abort(403)

    html = render_template('recu_remboursement_pdf.html', remboursement=remboursement, dette=dette)
    pdf_file = BytesIO()
    HTML(string=html).write_pdf(pdf_file)

    response = make_response(pdf_file.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=recu_remboursement_{remboursement.id}.pdf'
    return response


@app.route('/corbeille_dettes')
@login_required
def corbeille_dettes():
    dettes_supprimees = Dette.query.filter_by(utilisateur_id=current_user.id, supprime=True).all()
    return render_template("corbeille_dettes.html", dettes=dettes_supprimees)


@app.route("/restaurer_dette/<int:dette_id>", methods=["POST"])
@login_required
def restaurer_dette(dette_id):
    dette = Dette.query.get_or_404(dette_id)
    if dette.utilisateur_id != current_user.id:
        abort(403)
    dette.supprime = False
    db.session.commit()
    flash("Dette restaurée avec succès.", "success")
    return redirect(url_for("corbeille_dettes"))


@app.route("/supprimer_definitif_dette/<int:dette_id>", methods=["POST"])
@login_required
def supprimer_definitif_dette(dette_id):
    dette = Dette.query.get_or_404(dette_id)
    if dette.utilisateur_id != current_user.id:
        abort(403)

    # Supprimer d'abord les remboursements liés
    for remboursement in dette.remboursements:
        db.session.delete(remboursement)

    db.session.delete(dette)
    db.session.commit()

    flash("Dette supprimée définitivement.", "danger")
    return redirect(url_for("corbeille_dettes"))


import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/logos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def extension_autorisee(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/parametres_boutique', methods=['GET', 'POST'])
@login_required
def modifier_infos_boutique():
    if request.method == 'POST':
        current_user.nom_boutique = request.form.get('nom_boutique')
        current_user.adresse_boutique = request.form.get('adresse_boutique')
        current_user.telephone_boutique = request.form.get('telephone_boutique')

        # Traitement du logo
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file and extension_autorisee(logo_file.filename):
                filename = secure_filename(f"user_{current_user.id}_" + logo_file.filename)
                logo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logo_file.save(logo_path)
                current_user.logo = logo_path

        db.session.commit()
        flash("Informations de la boutique mises à jour.", "success")
        return redirect(url_for('index'))
    
    return render_template('parametres_boutique.html')

@app.route('/a_propos')
def a_propos():
    return render_template('a_propos.html')

@app.route('/recu/modifier/<int:recu_id>', methods=['GET', 'POST'])
@login_required
def modifier_recu(recu_id):
    recu = Recu.query.get_or_404(recu_id)

    if request.method == 'POST':
        recu.nom_client = request.form['nom_client']
        recu.telephone_client = request.form['telephone_client']

        montant_paye_str = request.form['montant_paye']
        monnaie_rendue_str = request.form['monnaie_rendue']

        recu.montant_paye = float(montant_paye_str) if montant_paye_str.strip() else 0.0
        recu.monnaie_rendue = float(monnaie_rendue_str) if monnaie_rendue_str.strip() else 0.0

        # ✅ Calcul du reste à payer
        reste_a_payer = recu.montant_total - recu.montant_paye

        if reste_a_payer > 0:
            # Si une dette existe déjà pour ce reçu, on la met à jour
            if recu.dette:
                recu.dette.montant_total = reste_a_payer
                recu.dette.client_nom = recu.nom_client
                recu.dette.client_telephone = recu.telephone_client
            else:
                # Sinon on en crée une nouvelle
                nouvelle_dette = Dette(
                    client_nom=recu.nom_client or "",
                    client_telephone=recu.telephone_client or "",
                    montant_total=reste_a_payer,
                    montant_rembourse=0,
                    recu_id=recu.id,
                    utilisateur_id=current_user.id
                )
                db.session.add(nouvelle_dette)
        else:
            # Si plus de dette, supprimer l'enregistrement dette s'il existe
            if recu.dette:
                db.session.delete(recu.dette)

        db.session.commit()
        flash('Reçu modifié avec succès', 'success')
        return redirect(url_for('recus'))

    return render_template('modifier_recu.html', recu=recu)

@app.route('/recu_ticket/<int:recu_id>')
@login_required
def recu_ticket(recu_id):
    recu = Recu.query.filter_by(id=recu_id, utilisateur_id=current_user.id).first_or_404()
    lignes = LigneVente.query.filter_by(recu_id=recu.id).all()
    return render_template('ticket_thermique.html', recu=recu, lignes=lignes)


@app.route("/archiver_stats")
@login_required
def archiver_stats():
    now = datetime.now()
    mois_actuel = now.strftime("%B %Y")
    
    # Recalculer les stats du mois actuel
    utilisateur_id = current_user.id
    chiffre_affaires = db.session.query(
        func.sum(LigneVente.quantite * LigneVente.prix_unitaire)
    ).join(Recu, LigneVente.recu_id == Recu.id)\
     .filter(
         Recu.utilisateur_id == utilisateur_id,
         extract('month', Recu.date_creation) == now.month,
         extract('year', Recu.date_creation) == now.year
     ).scalar() or 0
    
    total_achats = db.session.query(
        func.sum(LigneVente.quantite * Produit.prix_achat)
    ).join(Produit, LigneVente.produit_id == Produit.id)\
     .join(Recu, LigneVente.recu_id == Recu.id)\
     .filter(
         Recu.utilisateur_id == utilisateur_id,
         extract('month', Recu.date_creation) == now.month,
         extract('year', Recu.date_creation) == now.year
     ).scalar() or 0
    
    benefice = chiffre_affaires - total_achats
    marge = (benefice / chiffre_affaires * 100) if chiffre_affaires > 0 else 0
    
    nb_ventes = db.session.query(func.count(Recu.id)).filter(
        Recu.utilisateur_id == utilisateur_id,
        extract('month', Recu.date_creation) == now.month,
        extract('year', Recu.date_creation) == now.year
    ).scalar()
    
    # Vérifier si déjà archivé
    deja = ArchiveStat.query.filter_by(utilisateur_id=current_user.id, mois=mois_actuel).first()
    if deja:
        flash(f"❌ Les stats de {mois_actuel} sont déjà archivées.", "warning")
        return redirect(url_for("stats"))

    # Créer une nouvelle archive
    archive = ArchiveStat(
        utilisateur_id=current_user.id,
        mois=mois_actuel,
        chiffre_affaires=chiffre_affaires,
        total_achats=total_achats,
        benefice=benefice,
        marge=marge,
        nb_ventes=nb_ventes
    )
    db.session.add(archive)
    db.session.commit()
    
    flash(f"✅ Stats de {mois_actuel} archivées avec succès !", "success")
    return redirect(url_for("archives"))


@app.route("/archives")
@login_required
def archives():
    archives = ArchiveStat.query.filter_by(utilisateur_id=current_user.id)\
                .order_by(ArchiveStat.date_enregistrement.desc()).all()
    return render_template("archives.html", archives=archives)

# Route pour télécharger le PDF d'une archive spécifique
@app.route("/archives/<int:archive_id>/pdf")
@login_required
def telecharger_archive_pdf(archive_id):
    archive = ArchiveStat.query.filter_by(id=archive_id, utilisateur_id=current_user.id).first_or_404()

    # Générer un PDF simple basé sur cette archive (exemple minimal)
    rendered = render_template("rapport_archive_pdf.html", archive=archive)
    pdf = BytesIO()
    pisa.CreatePDF(BytesIO(rendered.encode("utf-8")), dest=pdf)
    response = make_response(pdf.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=rapport_archive_{archive.mois}.pdf"
    return response

# Route pour supprimer une archive
@app.route("/archives/<int:archive_id>/supprimer", methods=["POST"])
@login_required
def supprimer_archive(archive_id):
    archive = ArchiveStat.query.filter_by(id=archive_id, utilisateur_id=current_user.id).first_or_404()
    db.session.delete(archive)
    db.session.commit()
    flash(f"Archive {archive.mois} supprimée avec succès.", "success")
    return redirect(url_for("archives"))


from flask_migrate import upgrade

from flask_migrate import upgrade
from flask_login import login_required, current_user

@app.route("/run-migration")
def run_migration():
    return "✅ Route migration accessible (avant upgrade)"




# Lancement de l'application
if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)
