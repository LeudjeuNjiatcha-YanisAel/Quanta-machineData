# 🚀 MACHINE DATA HUB

Une plateforme analytique moderne développée avec **Flask**, **Pandas**, **Chart.js** et **Gemini AI** pour la gestion et l'analyse des données académiques.

## 🌟 Fonctionnalités
- **Tableau de Bord Dynamique** : Visualisation en temps réel avec 4 types de graphiques.
- **Analyse Prédictive IA** : Synthèse interactive générée par Google Gemini.
- **Web Scraping** : Importation automatisée de données via une API dédiée.
- **Thème Sombre/Clair** : Interface élégante avec mode Glassmorphism.
- **Rapports PDF** : Impression optimisée des résultats.

---

## 🛠️ Installation Locale

1. **Cloner le projet**
   ```bash
   git clone <votre-repo-url>
   cd TP_INF232_Pro
   ```

2. **Installer les dépendances**
   ```bash
   pip install flask pandas requests beautifulsoup4 google-generativeai python-dotenv
   ```

3. **Configurer les variables d'environnement**
   Créez un fichier `.env` à la racine et ajoutez :
   ```env
   GEMINI_API_KEY=Votre_Cle_Gemini
   SCRAPING_API_KEY=Votre_Cle_Scraping
   ```

4. **Lancer l'application**
   ```bash
   python app.py
   ```
   Accédez à `http://127.0.0.1:5000`

---

## 🌐 Déploiement sur Render.com

Pour déployer ce projet sur Render :

1. **Créer un fichier `requirements.txt`** :
   ```bash
   pip freeze > requirements.txt
   ```
2. **Ajouter un serveur WSGI** : Installez `gunicorn` :
   ```bash
   pip install gunicorn
   ```
3. **Sur Render** :
   - Connectez votre GitHub.
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn app:app`
   - **Environment Variables** : Ajoutez vos clés `.env` dans les paramètres de Render.

---

## 🕷️ Comment obtenir une API de Scraping ?

1. Rendez-vous sur [ScrapingAnt](https://scrapingant.com/) ou [ScrapingDog](https://www.scrapingdog.com/).
2. Inscrivez-vous gratuitement pour obtenir une **API Key**.
3. Copiez cette clé dans votre fichier `.env`.
4. L'API permet de contourner les protections anti-bot des sites web pour extraire les listes d'étudiants.

---

## 📝 Licence
Projet réalisé dans le cadre du cours INF232.
