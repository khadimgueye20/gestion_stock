from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)

# Configuration de la base de données SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stock.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "votre_cle_secrete"

db = SQLAlchemy(app)

# Modèle de produit
class Produit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    quantite = db.Column(db.Integer, nullable=False)

# Modèle de vente
class Vente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produit.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False, default=0)
    date_vente = db.Column(db.DateTime, default=datetime.utcnow)
    produit = db.relationship('Produit', backref=db.backref('ventes', lazy=True))
    

# Initialisation de Flask-Migrate
migrate = Migrate(app, db)

# Route principale
@app.route('/')
def index():
    produits = Produit.query.all()
    produits_rupture = Produit.query.filter(Produit.quantite == 0).all()
    return render_template('index.html', stock=produits, ruptures=produits_rupture)

# Route pour ajouter un produit
@app.route('/ajouter', methods=['POST'])
def ajouter():
    nom = request.form['nom']
    description = request.form['description']
    quantite = int(request.form['quantite'])
    nouveau_produit = Produit(nom=nom, description=description, quantite=quantite)
    db.session.add(nouveau_produit)
    db.session.commit()
    return redirect(url_for('index'))

# Route pour supprimer un produit par son ID
@app.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    produit = Produit.query.get_or_404(id)
    db.session.delete(produit)
    db.session.commit()
    return redirect(url_for('index'))

# Route pour modifier un produit
@app.route('/modifier/<int:id>', methods=['GET', 'POST'])
def modifier(id):
    produit = Produit.query.get_or_404(id)
    if request.method == 'POST':
        produit.nom = request.form['nom']
        produit.description = request.form['description']
        produit.quantite = int(request.form['quantite'])
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('modifier.html', produit=produit)

# Route pour vendre un produit
@app.route('/vendre/<int:id>', methods=['GET', 'POST'])
def vendre(id):
    produit = Produit.query.get_or_404(id)

    if request.method == 'POST':
        quantite_str = request.form.get('quantite')

        if not quantite_str or not quantite_str.isdigit():
            flash("Quantité invalide. Veuillez entrer un nombre positif.", "danger")
            return redirect(url_for('vendre', id=id))

        quantite_vendue = int(quantite_str)

        if quantite_vendue <= 0:
            flash("La quantité doit être supérieure à zéro.", "danger")
            return redirect(url_for('vendre', id=id))

        if quantite_vendue > produit.quantite:
            flash("Stock insuffisant pour cette vente.", "danger")
            return redirect(url_for('vendre', id=id))

        produit.quantite -= quantite_vendue

        vente = Vente(produit_id=produit.id, quantite=quantite_vendue, date_vente=datetime.utcnow())
        db.session.add(vente)
        db.session.commit()

        flash('Vente enregistrée avec succès.', 'success')
        return redirect(url_for('index'))

    return render_template('vendre.html', produit=produit)

# Route pour l'historique des ventes
from datetime import datetime

@app.route('/historique')
def historique():
    # Récupérer les paramètres de filtre dans l'URL
    produit_id = request.args.get('produit_id', type=int)
    date_debut_str = request.args.get('date_debut')
    date_fin_str = request.args.get('date_fin')

    # Construire la requête de base
    query = Vente.query

    # Filtrer par produit si produit_id est fourni
    if produit_id:
        query = query.filter(Vente.produit_id == produit_id)

    # Filtrer par date de début si fournie
    if date_debut_str:
        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d')
            query = query.filter(Vente.date_vente >= date_debut)
        except ValueError:
            flash("Format de date début invalide.", "danger")

    # Filtrer par date de fin si fournie
    if date_fin_str:
        try:
            # Pour inclure toute la journée de la date_fin, on ajoute 1 jour et on fait < date_fin+1
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d')
            date_fin = date_fin.replace(hour=23, minute=59, second=59)
            query = query.filter(Vente.date_vente <= date_fin)
        except ValueError:
            flash("Format de date fin invalide.", "danger")

    # Trier par date de vente décroissante
    ventes = query.order_by(Vente.date_vente.desc()).all()

    # Pour le formulaire, récupérer tous les produits pour la liste déroulante
    produits = Produit.query.all()

    # Passer les paramètres à la template pour garder les valeurs dans le formulaire
    return render_template('historique.html',
                           ventes=ventes,
                           produits=produits,
                           produit_id=produit_id,
                           date_debut=date_debut_str,
                           date_fin=date_fin_str)


#Route pour supprimer une vente
@app.route('/supprimer_vente/<int:id>', methods=['POST'])
def supprimer_vente(id):
    vente = Vente.query.get_or_404(id)
    db.session.delete(vente)
    db.session.commit()
    flash("Vente supprimée avec succès.", "success")
    return redirect(url_for('historique'))

# Route pour supprimer toutes les ventes
@app.route('/supprimer_toutes_ventes', methods=['POST'])
def supprimer_toutes_ventes():
    Vente.query.delete()
    db.session.commit()
    flash("Historique des ventes supprimé.", "success")
    return redirect(url_for('historique'))


if __name__ == '__main__':
    with app.app_context():
     app.run(debug=True)
