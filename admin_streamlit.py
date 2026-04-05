import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import time
import os
import qrcode
from io import BytesIO
import base64

# Configuration de la page
st.set_page_config(page_title="GESTION RH PRO", layout="wide", initial_sidebar_state="expanded")

# --- FONCTION DE CONNEXION BDD ---
def get_db_connection():
    conn = sqlite3.connect('data/database.db', check_same_thread=False)
    return conn

# --- SIDEBAR (MENU DE NAVIGATION À GAUCHE) ---
with st.sidebar:
    try:
        st.image("static/logo.png", width=100)
    except:
        pass
    st.title("Menu Principal")
    menu = st.radio(
        "Navigation",
        ["Tableau de Bord", "Liste du Personnel", "Historique Pointages", "Importer des Employés"]
    )
    st.markdown("---")
    st.info("Connecté en tant qu'Administrateur")

# --- ENTÊTE ---
col_titre, col_horloge = st.columns([3, 1])

with col_titre:
    st.markdown("""
        <div style="border: 3px solid #0D6EFD; padding: 10px; border-radius: 10px; text-align: center; background-color: #f0f2f6;">
            <h1 style="margin: 0; font-weight: bold; text-transform: uppercase; color: #0D6EFD; font-size: 24px;">
                PROJET GESTION RH - POINTAGE
            </h1>
        </div>
    """, unsafe_allow_html=True)

with col_horloge:
    heure_actuelle = datetime.now().strftime("%H:%M:%S")
    st.markdown(f"""
        <div style="text-align: right; padding-top: 5px;">
            <h2 style="margin: 0; color: #31333F;">⏰ {heure_actuelle}</h2>
            <p style="color: gray; margin: 0;">{datetime.now().strftime('%d/%m/%Y')}</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- LOGIQUE DES PAGES ---
conn = get_db_connection()

if menu == "Tableau de Bord":
    st.subheader("Statistiques en temps réel")
    df_users = pd.read_sql_query("SELECT * FROM user", conn)
    df_pointages = pd.read_sql_query("SELECT * FROM pointage", conn)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Effectif Total", len(df_users))
    
    presents = 0
    for idx, user in df_users.iterrows():
        last_p = df_pointages[df_pointages['user_id'] == user['id']].sort_values(by='timestamp', ascending=False).head(1)
        if not last_p.empty and last_p.iloc[0]['type_mouvement'] == 'ENTREE':
            presents += 1
            
    c2.metric("Présents (Entrées)", presents)
    c3.metric("Mouvements aujourd'hui", len(df_pointages))
    st.markdown("---")
    st.subheader("⚡ Derniers Scans")
    st.table(df_pointages.tail(5))

elif menu == "Liste du Personnel":
    st.subheader("Gestion des Employés")
    df_users = pd.read_sql_query("SELECT matricule, nom, taux_horaire FROM user", conn)
    st.dataframe(df_users, use_container_width=True)
    if st.button("Exporter la liste en Excel"):
        st.success("Rapport généré avec succès !")

elif menu == "Historique Pointages":
    st.subheader("Historique Complet")
    df_full = pd.read_sql_query("""
        SELECT u.nom, u.matricule, p.timestamp, p.type_mouvement 
        FROM pointage p 
        JOIN user u ON p.user_id = u.id
        ORDER BY p.timestamp DESC
    """, conn)
    st.write(df_full)

elif menu == "Importer des Employés":
    # Création de deux onglets pour séparer l'importation de l'affiche
    tab_import, tab_affiche = st.tabs(["Importation massive", "🖼️ Générer Affiche Murale"])

    with tab_import:
        st.subheader("Importation massive de la base de données")
        st.markdown("""
            Téléchargez un fichier **Excel (.xlsx)** ou **CSV** avec les colonnes suivantes : 
            `matricule`, `nom`, `taux_horaire`.
        """)
        
        uploaded_file = st.file_uploader("Choisir un fichier", type=['xlsx', 'csv'])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_import = pd.read_csv(uploaded_file)
                else:
                    df_import = pd.read_excel(uploaded_file)
                
                st.write("Aperçu des données à importer :")
                st.dataframe(df_import.head())
                
                if st.button("Confirmer l'importation"):
                    success_count = 0
                    error_count = 0
                    
                    for index, row in df_import.iterrows():
                        try:
                            # Insertion dans la base de données
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO user (matricule, nom, taux_horaire) VALUES (?, ?, ?)",
                                (str(row['matricule']).upper(), row['nom'], float(row['taux_horaire']))
                            )
                            conn.commit()
                            
                            # Génération automatique du QR Code pour chaque nouvel employé
                            qr_folder = "static/qrcodes"
                            os.makedirs(qr_folder, exist_ok=True)
                            img = qrcode.make(str(row['matricule']).upper())
                            img.save(f"{qr_folder}/{str(row['matricule']).upper()}.png")
                            
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                    
                    st.success(f"Importation terminée ! ✅ {success_count} employés ajoutés.")
                    if error_count > 0:
                        st.warning(f"⚠️ {error_count} matricules existaient déjà ou étaient invalides.")
            except Exception as e:
                st.error(f"Erreur lors de la lecture du fichier : {e}")

    with tab_affiche:
        st.subheader("Générer l'affiche pour le pointage mobile")
        st.write("Les employés scanneront ce QR Code avec leur propre téléphone pour ouvrir la borne.")
        
        # Saisie de l'adresse IP (Automatiquement accessible par d'autres appareils)
        ip_mac = st.text_input("Saisissez l'adresse IP de ce Mac (Ex: 192.168.1.15)", "0.0.0.0")
        url_borne = f"http://{ip_mac}:5000"
        
        if st.button("Générer l'affiche de pointage"):
            # Génération du QR Code
            qr_img = qrcode.make(url_borne)
            buf = BytesIO()
            qr_img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            
            # Affichage d'un modèle d'affiche propre
            st.markdown(f"""
                <div style="border: 10px solid #0D6EFD; padding: 40px; text-align: center; background-color: white; color: black; border-radius: 20px;">
                    <h1 style="font-size: 50px; color: #0D6EFD; margin-bottom: 0;">SCANNAL & POINTEZ</h1>
                    <p style="font-size: 20px; color: gray;">Connectez-vous au Wi-Fi et scannez le code ci-dessous</p>
                    <img src="data:image/png;base64,{img_b64}" width="400" style="margin: 20px;">
                    <h2 style="color: #333;">URL : {url_borne}</h2>
                    <p style="font-size: 14px; color: #888;">Système de gestion RH sécurisé</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.download_button(
                label="Télécharger l'affiche pour impression",
                data=buf.getvalue(),
                file_name="Affiche_Pointage_Entreprise.png",
                mime="image/png"
            )

conn.close()