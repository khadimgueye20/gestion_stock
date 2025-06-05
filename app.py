from flask import Flask, abort, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from flask_mail import Mail, Message

app = Flask(__name__)

# Configuration de la base de données PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:touba202@localhost:5432/gestion_stock'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "votre_cle_secrete"

# Configuration pour Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'gkhadim202@gmail.com'
app.config['MAIL_PASSWORD'] = 'wmrt ennr txgn sfkr'
app.config['MAIL_DEFAULT_SENDER'] = 'gkhadim202@gmail.com'
mail = Mail(app)

# Initialisation des extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modèle Utilisateur
class Utilisateur(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nom_utilisateur = db.Column(db.String(80), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100))
    role = db.Column(db.String(20), nullable=False, default='utilisateur')

# Modèle Produit
class Produit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    supprime = db.Column(db.Boolean, default=False)

# Modèle Vente
class Vente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produit.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False, default=0)
    date_vente = db.Column(db.DateTime, default=datetime.utcnow)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    produit = db.relationship('Produit', backref=db.backref('ventes', lazy=True, cascade="all, delete"))
    supprime = db.Column(db.Boolean, default=False)

# Chargement utilisateur
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Utilisateur, int(user_id))

# Route principale
@app.route('/')
@login_required
def index():
    produits = Produit.query.filter_by(utilisateur_id=current_user.id, supprime=False).all()
    produits_rupture = Produit.query.filter_by(utilisateur_id=current_user.id, quantite=0, supprime=False).all()
    return render_template('index.html', stock=produits, ruptures=produits_rupture)

# Route historique
@app.route('/historique')
@login_required
def historique():
    produit_id = request.args.get('produit_id', type=int)
    date_debut_str = request.args.get('date_debut')
    date_fin_str = request.args.get('date_fin')

    query = Vente.query.filter_by(utilisateur_id=current_user.id, supprime=False)

    if produit_id:
        query = query.filter_by(produit_id=produit_id)

    if date_debut_str:
        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d')
            query = query.filter(Vente.date_vente >= date_debut)
        except ValueError:
            flash("Format de date début invalide.", "danger")

    if date_fin_str:
        try:
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(Vente.date_vente <= date_fin)
        except ValueError:
            flash("Format de date fin invalide.", "danger")

    ventes = query.order_by(Vente.date_vente.desc()).all()
    produits = Produit.query.filter_by(utilisateur_id=current_user.id, supprime=False).all()

    return render_template(
        'historique.html',
        ventes=ventes,
        produits=produits,
        produit_id=produit_id,
        date_debut=date_debut_str,
        date_fin=date_fin_str
    )


# Route pour ajouter un produit
@app.route('/ajouter', methods=['POST'])
@login_required
def ajouter():
    nom = request.form['nom']
    description = request.form['description']
    quantite = int(request.form['quantite'])
    prix_unitaire = float(request.form.get('prix_unitaire', 0.0))
    
    nouveau_produit = Produit(
        nom=nom,
        description=description,
        quantite=quantite,
        prix_unitaire=prix_unitaire,
        utilisateur_id=current_user.id  
    )
    
    db.session.add(nouveau_produit)
    db.session.commit()
    flash("Produit ajouté avec succès.", "success")
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



# Route pour modifier un produit
@app.route('/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier(id):
    produit = Produit.query.get_or_404(id)
    
    if produit.utilisateur_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        # Stocker les anciennes valeurs
        ancien_nom = produit.nom
        ancienne_description = produit.description
        ancienne_quantite = produit.quantite
        ancien_prix = produit.prix_unitaire

        # Nouvelles valeurs depuis le formulaire
        nouveau_nom = request.form['nom']
        nouvelle_description = request.form['description']
        nouvelle_quantite = int(request.form['quantite'])
        nouveau_prix = float(request.form['prix_unitaire'])

        # Préparer le résumé des modifications
        changements = []
        if ancien_nom != nouveau_nom:
            changements.append(f"- Nom : '{ancien_nom}' → '{nouveau_nom}'")
        if ancienne_description != nouvelle_description:
            changements.append(f"- Description modifiée")
        if ancienne_quantite != nouvelle_quantite:
            changements.append(f"- Quantité : {ancienne_quantite} → {nouvelle_quantite}")
        if ancien_prix != nouveau_prix:
            changements.append(f"- Prix unitaire : {ancien_prix} → {nouveau_prix} FCFA")

        # Appliquer les modifications
        produit.nom = nouveau_nom
        produit.description = nouvelle_description
        produit.quantite = nouvelle_quantite
        produit.prix_unitaire = nouveau_prix

        db.session.commit()

        # Envoi de mail si au moins un changement a eu lieu
        if changements:
            corps_message = "Le produit a été modifié avec les changements suivants :\n\n" + "\n".join(changements)
            msg = Message(
                subject="Produit modifié",
                recipients=[current_user.email],
                body=corps_message
            )
            mail.send(msg)

        flash("Produit modifié avec succès.", "success")
        return redirect(url_for('index'))

    return render_template('modifier.html', produit=produit)



@app.route('/vendre/<int:id>', methods=['GET', 'POST'])
@login_required
def vendre(id):
    produit = Produit.query.get_or_404(id)
    
    # Sécurité : s'assurer que le produit appartient à l'utilisateur
    if produit.utilisateur_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        quantite_str = request.form.get('quantite')
        if not quantite_str or not quantite_str.isdigit():
            flash("Quantité invalide.", "danger")
            return redirect(url_for('vendre', id=id))

        quantite_vendue = int(quantite_str)
        if quantite_vendue <= 0:
            flash("La quantité doit être supérieure à zéro.", "danger")
            return redirect(url_for('vendre', id=id))
        if quantite_vendue > produit.quantite:
            flash("Stock insuffisant.", "danger")
            return redirect(url_for('vendre', id=id))

        produit.quantite -= quantite_vendue
        vente = Vente(
            produit_id=produit.id,
            quantite=quantite_vendue,
            utilisateur_id=current_user.id  
        )
        db.session.add(vente)
        db.session.commit()
        flash("Vente enregistrée avec succès.", "success")
        return redirect(url_for('index'))
        
    return render_template('vendre.html', produit=produit)



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
    return render_template('login.html')

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

        if not nom_utilisateur or not email or not mot_de_passe:
            flash("Tous les champs sont obligatoires.", "danger")
            return redirect(url_for('register'))

        if Utilisateur.query.filter_by(nom_utilisateur=nom_utilisateur).first():
            flash("Ce nom d'utilisateur existe déjà.", "warning")
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

    return render_template('register.html')


@app.route('/admin/utilisateurs')
def liste_utilisateurs():
    utilisateurs = Utilisateur.query.all()
    return render_template('admin_utilisateurs.html', utilisateurs=utilisateurs)

@app.route('/corbeille')
@login_required
def corbeille():
    produits_supprimes = Produit.query.filter_by(utilisateur_id=current_user.id, supprime=True).all()
    ventes_supprimees = Vente.query.filter_by(utilisateur_id=current_user.id, supprime=True).all()
    return render_template('corbeille.html', produits=produits_supprimes, ventes=ventes_supprimees)

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



# Lancement de l'application
if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)
