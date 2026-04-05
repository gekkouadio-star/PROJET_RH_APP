# Système de Gestion RH & Pointage par QR Code

Ce projet est une solution logicielle complète permettant de gérer les temps de présence en entreprise. Il combine la puissance de **Flask** pour la capture de données en temps réel et **Streamlit** pour le pilotage administratif.

---

## Fonctionnalités Clés

### 🕒 Pointage Hybride
* **Borne Fixe :** Interface de scan via la caméra du Mac/PC (Flask).
* **Pointage Mobile :** Affiche murale avec QR Code permettant aux employés de pointer avec leur propre smartphone.

### Dashboard Administrateur (Streamlit)
* **Statistiques en temps réel :** Nombre d'employés présents, flux d'activité.
* **Interface Pro :** Titre encadré, menu de navigation latéral et horloge dynamique.
* **Historique :** Journal complet des entrées/sorties avec recherche.

### 🗂️ Gestion des Données
* **Importation Massive :** Chargement de la base employés via fichiers **Excel** ou **CSV**.
* **Génération Automatique :** Création instantanée des badges QR Code individuels lors de l'import.
* **Exports :** Extraction des rapports de présence au format Excel.

---

## Installation & Configuration

### 1. Prérequis
* Python 3.10+
* Navigateur Web (Chrome, Safari, Firefox)

### 2. Mise en place
```bash
# Accéder au dossier du projet
cd PROJET_RH_APP

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt