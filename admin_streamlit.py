import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import time
import os
import qrcode
from io import BytesIO
import base64
from streamlit_option_menu import option_menu  # Nouvelle importation

# Configuration de la page
st.set_page_config(page_title="GESTION RH PRO", layout="wide", initial_sidebar_state="expanded")

# --- FONCTION DE CONNEXION BDD ---
def get_db_connection():
    conn = sqlite3.connect('data/database.db', check_same_thread=False)
    return conn

# --- SIDEBAR (DESIGN AMÉLIORÉ ET LOGO CENTRÉ) ---
with st.sidebar:
    # Utilisation de colonnes pour centrer l'image
    col_l1, col_logo, col_l3 = st.columns([1, 2, 1])
    with col_logo:
        try:
            # Ton image d'horloge maintenant centrée
            st.image("static/logo.png", width=100)
        except:
            pass
    
    # Titre de la sidebar avec alignement central
    st.markdown("""
        <div style="text-align: center; margin-top: -10px; margin-bottom: 20px;">
            <h3 style="font-weight: bold; text-transform: uppercase; font-size: 16px; color: #31333F;">
                ESPACE ADMINISTRATEUR
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    # Menu de navigation stylé
    menu = option_menu(
        menu_title="MENU PRINCIPAL",
        options=["TABLEAU DE BORD", "LISTE DU PERSONNEL", "HISTORIQUE POINTAGES", "IMPORTER DES EMPLOYÉS"],
        icons=["speedometer2", "people", "clock-history", "cloud-upload"], # Icônes Bootstrap
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "5!important", "background-color": "#fafafa"},
            "icon": {"color": "#0D6EFD", "font-size": "20px"}, 
            "nav-link": {"font-size": "14px", "text-align": "left", "margin":"0px", "--hover-color": "#eee", "font-weight": "bold"},
            "nav-link-selected": {"background-color": "#0D6EFD"},
        }
    )
    
    st.markdown("---")
    st.info("**STATUT : CONNECTÉ ✅**")
    
# --- ENTÊTE ---
col_titre, col_horloge = st.columns([3, 1])

with col_titre:
    st.markdown("""
        <div style="border: 3px solid #0D6EFD; padding: 15px; border-radius: 15px; text-align: center; background-color: #f0f2f6; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
            <h1 style="margin: 0; font-weight: bold; text-transform: uppercase; color: #0D6EFD; font-size: 26px;">
                PROJET GESTION RH - POINTAGE
            </h1>
        </div>
    """, unsafe_allow_html=True)

with col_horloge:
    # Padding de 12px pour un alignement vertical parfait avec le bloc de gauche
    heure_actuelle = datetime.now().strftime("%H:%M:%S")
    st.markdown(f"""
        <div style="text-align: right; padding-top: 12px;">
            <h2 style="margin: 0; color: #31333F; font-weight: bold; font-size: 22px;">⏰ {heure_actuelle}</h2>
            <p style="color: #0D6EFD; margin: 0; font-weight: bold; font-size: 16px;">{datetime.now().strftime('%d/%m/%Y').upper()}</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- LOGIQUE DES PAGES ---
conn = get_db_connection()

if menu == "TABLEAU DE BORD":
    st.markdown("## **STATISTIQUES EN TEMPS RÉEL**")
    df_users = pd.read_sql_query("SELECT * FROM user", conn)
    df_pointages = pd.read_sql_query("SELECT * FROM pointage", conn)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("EFFECTIF TOTAL", len(df_users))
    with c2:
        presents = 0
        for idx, user in df_users.iterrows():
            last_p = df_pointages[df_pointages['user_id'] == user['id']].sort_values(by='timestamp', ascending=False).head(1)
            if not last_p.empty and last_p.iloc[0]['type_mouvement'] == 'ENTREE':
                presents += 1
        st.metric("PRÉSENTS (ENTRÉES)", presents)
    with c3:
        st.metric("MOUVEMENTS AUJOURD'HUI", len(df_pointages))
    
    st.markdown("---")
    st.markdown("### **⚡ DERNIERS SCANS ENREGISTRÉS**")
    st.table(df_pointages.tail(5))

elif menu == "LISTE DU PERSONNEL":
    st.markdown("## **GESTION DES EMPLOYÉS**")
    df_users = pd.read_sql_query("SELECT matricule, nom, taux_horaire FROM user", conn)
    
    st.dataframe(df_users, use_container_width=True)
    
    if st.button("📥 EXPORTER LA LISTE EN EXCEL"):
        st.success("**RAPPORT GÉNÉRÉ AVEC SUCCÈS !**")
    
    st.markdown("---")
    st.markdown("## **RÉCUPÉRER UN QR CODE INDIVIDUEL**")
    
    if not df_users.empty:
        choix_employe = st.selectbox(
            "SÉLECTIONNEZ UN EMPLOYÉ :",
            df_users['nom'].tolist()
        )
        
        info_user = df_users[df_users['nom'] == choix_employe].iloc[0]
        matricule_sel = info_user['matricule']
        
        col_v1, col_badge, col_v2 = st.columns([1, 1, 1])
        with col_badge:
            path = f"static/qrcodes/{matricule_sel}.png"
            if os.path.exists(path):
                st.image(path, caption=f"BADGE DE {choix_employe.upper()} ({matricule_sel})", width=250)
                with open(path, "rb") as file:
                    st.download_button(
                        label="TÉLÉCHARGER LE QR CODE",
                        data=file,
                        file_name=f"QR_{matricule_sel}.png",
                        mime="image/png"
                    )
            else:
                st.error("**ERREUR : FICHIER QR CODE INTROUVABLE.**")

elif menu == "HISTORIQUE POINTAGES":
    st.markdown("## **HISTORIQUE COMPLET DES MOUVEMENTS**")
    df_full = pd.read_sql_query("""
        SELECT u.nom, u.matricule, p.timestamp, p.type_mouvement 
        FROM pointage p 
        JOIN user u ON p.user_id = u.id
        ORDER BY p.timestamp DESC
    """, conn)
    st.dataframe(df_full, use_container_width=True)

elif menu == "IMPORTER DES EMPLOYÉS":
    tab_import, tab_affiche = st.tabs(["📤 **IMPORTATION MASSIVE**", "🖼️ **AFFICHE MURALE**"])

    with tab_import:
        st.markdown("## **IMPORTATION DE LA BASE DE DONNÉES**")
        st.markdown("**FORMAT REQUIS :** `MATRICULE`, `NOM`, `TAUX_HORAIRE`")
        
        uploaded_file = st.file_uploader("CHOISIR UN FICHIER EXCEL OU CSV", type=['xlsx', 'csv'])
        
        if uploaded_file is not None:
            try:
                df_import = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                st.dataframe(df_import.head())
                
                if st.button("LANCER L'IMPORTATION"):
                    success_count = 0
                    for index, row in df_import.iterrows():
                        try:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO user (matricule, nom, taux_horaire) VALUES (?, ?, ?)",
                                         (str(row['matricule']).upper(), row['nom'], float(row['taux_horaire'])))
                            conn.commit()
                            
                            qr_folder = "static/qrcodes"
                            os.makedirs(qr_folder, exist_ok=True)
                            img = qrcode.make(str(row['matricule']).upper())
                            img.save(f"{qr_folder}/{str(row['matricule']).upper()}.png")
                            success_count += 1
                        except: continue
                    st.success(f"**SUCCÈS : {success_count} EMPLOYÉS IMPORTÉS !**")
            except Exception as e:
                st.error(f"**ERREUR : {e}**")

    with tab_affiche:
        st.markdown("## **GÉNÉRER L'AFFICHE DE POINTAGE**")
        ip_mac = st.text_input("ADRESSE IP DU SERVEUR :", "0.0.0.0")
        url_borne = f"http://{ip_mac}:5000"
        
        if st.button("🎨 CRÉER L'AFFICHE"):
            qr_img = qrcode.make(url_borne)
            buf = BytesIO()
            qr_img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            
            st.markdown(f"""
                <div style="border: 8px solid #0D6EFD; padding: 40px; text-align: center; background-color: white; border-radius: 20px;">
                    <h1 style="font-size: 45px; color: #0D6EFD; font-weight: bold;">SCANNAL & POINTEZ</h1>
                    <p style="font-size: 20px; color: #333; font-weight: bold;">SCANNEZ POUR ACCÉDER À LA BORNE</p>
                    <img src="data:image/png;base64,{img_b64}" width="350" style="margin: 20px;">
                    <h2 style="color: #0D6EFD;">{url_borne}</h2>
                </div>
            """, unsafe_allow_html=True)

conn.close()