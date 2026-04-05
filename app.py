from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import pandas as pd
import qrcode

# Charge les variables du fichier .env
load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key-7b9e2c1a4f0d')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['EXPORT_FOLDER'] = os.path.join(basedir, 'exports')

db = SQLAlchemy(app)

# --- MODELES DE DONNEES ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(20), unique=True, nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    taux_horaire = db.Column(db.Float, default=10.0)
    pointages = db.relationship('Pointage', backref='employe', lazy=True)

class Pointage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    type_mouvement = db.Column(db.String(10)) # 'ENTREE' ou 'SORTIE'

# --- ROUTES FRONTEND (POINTAGE) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pointer', methods=['POST'])
def pointer():
    matricule = request.form.get('matricule').strip().upper() 
    user = User.query.filter_by(matricule=matricule).first()

    if not user:
        flash(f"Erreur : Le matricule {matricule} n'existe pas.", "danger")
        return redirect(url_for('index'))

    dernier_p = Pointage.query.filter_by(user_id=user.id).order_by(Pointage.timestamp.desc()).first()

    # SECURITE : 2 minutes entre deux scans
    if dernier_p:
        diff = datetime.now() - dernier_p.timestamp
        if diff.total_seconds() < 120:
            flash("Action trop rapide ! Attendez 2 minutes.", "warning")
            return redirect(url_for('index'))

    type_m = 'ENTREE'
    if dernier_p and dernier_p.type_mouvement == 'ENTREE':
        type_m = 'SORTIE'

    nouveau_pointage = Pointage(user_id=user.id, type_mouvement=type_m)
    db.session.add(nouveau_pointage)
    db.session.commit()

    flash(f"Succès ! {user.nom} : {type_m} enregistrée à {datetime.now().strftime('%H:%M')}", "success")
    return redirect(url_for('index'))

# --- ROUTES ADMIN ---

@app.route('/admin')
def admin():
    # --- AJOUT SECURITE MOT DE PASSE ---
    # Pour accéder, il faudra utiliser : /admin?pw=1234
    password = request.args.get('pw')
    if password != "1234": 
        return "<h1>Accès refusé</h1><p>Vous n'avez pas l'autorisation de consulter cette page sans le code secret.</p>", 403

    users = User.query.all()
    presents = 0
    for user in users:
        dernier = Pointage.query.filter_by(user_id=user.id).order_by(Pointage.timestamp.desc()).first()
        if dernier and dernier.type_mouvement == 'ENTREE':
            presents += 1
            
    derniers_scans = Pointage.query.order_by(Pointage.timestamp.desc()).limit(5).all()
    
    return render_template('admin.html', 
                           users=users, 
                           presents=presents, 
                           derniers_scans=derniers_scans, 
                           now=datetime.now())
    
@app.route('/add_user', methods=['POST'])
def add_user():
    nom = request.form.get('nom')
    matricule = request.form.get('matricule').strip().upper()
    taux = request.form.get('taux')
    
    if nom and matricule:
        try:
            new_user = User(nom=nom, matricule=matricule, taux_horaire=float(taux))
            db.session.add(new_user)
            db.session.commit()

            qr_folder = os.path.join(basedir, 'static', 'qrcodes')
            os.makedirs(qr_folder, exist_ok=True)
            qr_path = os.path.join(qr_folder, f"{matricule}.png")
            img = qrcode.make(matricule)
            img.save(qr_path)

            flash(f"✅ Employé {nom} ajouté !", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")
    
    return redirect(url_for('admin'))

@app.route('/export_excel')
def export_excel():
    users = User.query.all()
    final_data = []

    for user in users:
        ps = Pointage.query.filter_by(user_id=user.id).order_by(Pointage.timestamp.asc()).all()
        entree = None
        for p in ps:
            if p.type_mouvement == 'ENTREE':
                entree = p.timestamp
            elif p.type_mouvement == 'SORTIE' and entree:
                sortie = p.timestamp
                duree = sortie - entree
                heures_decimales = duree.total_seconds() / 3600
                gain = heures_decimales * user.taux_horaire
                
                final_data.append({
                    'Matricule': user.matricule,
                    'Nom': user.nom,
                    'Date': entree.strftime('%d/%m/%Y'),
                    'Arrivée': entree.strftime('%H:%M'),
                    'Départ': sortie.strftime('%H:%M'),
                    'Durée (H)': round(heures_decimales, 2),
                    'Taux Horaire': f"{user.taux_horaire} €",
                    'Salaire Total': f"{round(gain, 2)} €"
                })
                entree = None

    if not final_data:
        flash("Aucun cycle complet trouvé.", "warning")
        return redirect(url_for('admin'))

    df = pd.DataFrame(final_data)
    filename = f"Paie_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
    df.to_excel(filepath, index=False)
    return send_from_directory(directory=app.config['EXPORT_FOLDER'], path=filename, as_attachment=True)

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    user = User.query.get_or_4_404(user_id)
    try:
        # 1. Supprimer le fichier image du QR Code
        qr_path = os.path.join(basedir, 'static', 'qrcodes', f"{user.matricule}.png")
        if os.path.exists(qr_path):
            os.remove(qr_path)
        
        # 2. Supprimer les pointages associés (cascade)
        Pointage.query.filter_by(user_id=user.id).delete()
        
        # 3. Supprimer l'utilisateur
        db.session.delete(user)
        db.session.commit()
        flash(f"L'employé {user.nom} a été supprimé avec succès.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
        
    return redirect(url_for('admin'))

# --- LANCEMENT AVEC ACCÈS RÉSEAU ---
if __name__ == '__main__':
    with app.app_context():
        os.makedirs(os.path.join(basedir, 'data'), exist_ok=True)
        os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)
        db.create_all() 
    # host='0.0.0.0' permet à n'importe quel appareil sur ton Wi-Fi d'accéder au site
    app.run(debug=True, host='0.0.0.0', port=5000)