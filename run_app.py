import subprocess
import sys
import time
import os

def start_apps():
    print("Démarrage du Système RH Hybride...")
    print("---------------------------------------")

    # 1. Lancer le serveur Flask (Pointage)
    # On utilise sys.executable pour être sûr d'utiliser le Python du venv
    print("Lancement de la Borne de Pointage (Flask) sur le port 5000...")
    flask_process = subprocess.Popen([sys.executable, "app.py"])

    # Petite pause pour laisser Flask démarrer
    time.sleep(2)

    # 2. Lancer le Dashboard Admin (Streamlit)
    print("Lancement du Dashboard Admin (Streamlit) sur le port 8501...")
    # Streamlit nécessite d'être lancé avec son propre module
    streamlit_process = subprocess.Popen(["streamlit", "run", "admin_streamlit.py"])

    print("---------------------------------------")
    print("✅ TOUT EST OPÉRATIONNEL !")
    print("👉 Borne : http://localhost:5000")
    print("👉 Admin : http://localhost:8501")
    print("👉 IP Réseau : http://192.168.1.75:5000")
    print("---------------------------------------")
    print("Appuyez sur CTRL+C pour tout arrêter.")

    try:
        # Garde le script actif pour que les processus continuent de tourner
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt des services...")
        flask_process.terminate()
        streamlit_process.terminate()
        print("👋 Au revoir !")

if __name__ == "__main__":
    start_apps()