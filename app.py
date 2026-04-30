from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import google.generativeai as genai
import pandas as pd
import json
import requests
from bs4 import BeautifulSoup
import random
import os
import time
import threading
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY","").split(",")
index = 0
SCRAPING_API_KEY = os.getenv("SCRAPING_API_KEY")


# Creation de ma base de donnees
def init_db():
    '''
    Initialisation de la base de données avec les nouvelles variables.
    '''
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            sexe TEXT,
            ville TEXT,
            niveau TEXT,
            filiere TEXT NOT NULL,
            moyenne REAL NOT NULL, 
            temps REAL NOT NULL,
            age INTEGER NOT NULL,
            participation INTEGER DEFAULT 0,
            sommeil REAL DEFAULT 7.0,
            distraction TEXT DEFAULT 'Aucune'
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def accueil():
    """ Affiche la page d'accueil simple """
    return render_template('accueil.html')

@app.route('/collecte')
def collecte():
    """ Affiche le formulaire d'ajout ou de modification """
    edit_id = request.args.get('edit_id')
    edit_student = None
    
    if edit_id:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE id=?", (edit_id,))
        raw_student = cursor.fetchone()
        conn.close()
        
        if raw_student:
            edit_student = {
                'id': raw_student[0], 'nom': raw_student[1], 'prenom': raw_student[2],
                'sexe': raw_student[3], 'ville': raw_student[4], 'niveau': raw_student[5],
                'filiere': raw_student[6], 'moyenne': raw_student[7], 
                'temps': raw_student[8], 'age': raw_student[9], 'participation': raw_student[10],
                'sommeil': raw_student[11] if len(raw_student) > 11 else 7.0,
                'distraction': raw_student[12] if len(raw_student) > 12 else 'Aucune'
            }

    return render_template('collecte.html', edit_student=edit_student)

def key_rotation():
    global index
    if not GEMINI_API_KEY or GEMINI_API_KEY == [""]:
        return None
    key = GEMINI_API_KEY[index]
    index = (index + 1) % len(GEMINI_API_KEY)
    print(f'Cle {index} qui a ete utilser')
    return key

@app.route('/resultats')
def resultats():
    """ Affiche les statistiques, graphiques et la base de données complète """
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()

    if df.empty:
        return render_template('resultats.html', data=[], stats={}, chart_data="{}")

    try:
        stats = {
            "total_etudiants": len(df),
            "moyenne_generale": round(df["moyenne"].mean(), 2),
            "age_moyen": round(df["age"].mean(), 2),
            "temps_etude_moyen": round(df["temps"].mean(), 2),
            "participation_moyenne": round(df["participation"].mean(), 2) if "participation" in df else 0,
            "meilleure_moyenne": round(df["moyenne"].max(), 2),
            "pire_moyenne": round(df["moyenne"].min(), 2),
            "sexe_ratio": df['sexe'].value_counts().to_dict() if 'sexe' in df else {}
        }
    except Exception as e:
        print(f"Erreur stats: {e}")
        stats = {} 

    chart_data = {
        "filieres": df['filiere'].value_counts().to_dict(),
        "niveaux": df['niveau'].value_counts().to_dict() if 'niveau' in df else {},
        "temps_vs_moyenne": [{"x": row['temps'], "y": row['moyenne']} for index, row in df.iterrows()],
        "participation_dist": df['participation'].tolist() if 'participation' in df else [],
        "age_moyenne": df.groupby('age')['moyenne'].mean().to_dict()
    }

    return render_template(
        'resultats.html', 
        data=df.values.tolist(), 
        stats=stats, 
        chart_data=json.dumps(chart_data)
    )

@app.route('/api/analyse')
def api_analyse():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()

    if df.empty:
        return json.dumps({"summary": "Aucune donnée disponible pour l'analyse.", "risks": "N/A", "recommendations": "N/A"})

    stats = {
        "total_etudiants": len(df),
        "moyenne_generale": round(df["moyenne"].mean(), 2),
        "age_moyen": round(df["age"].mean(), 2),
        "temps_etude_moyen": round(df["temps"].mean(), 2),
        "moyenne_par_filiere": df.groupby("filiere")["moyenne"].mean().to_dict(),
        "moyenne_par_niveau": df.groupby("niveau")["moyenne"].mean().to_dict(),
        "meilleur_etudiant": df.loc[df["moyenne"].idxmax()][["nom", "prenom", "moyenne"]].to_dict(),
        "pire_etudiant": df.loc[df["moyenne"].idxmin()][["nom", "prenom", "moyenne"]].to_dict(),
        "participation_moyenne": round(df["participation"].mean(), 2) if "participation" in df else 0
    }

    try:
        api_key = key_rotation()
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"""
             Tu es un expert en analyse statistique et en education: {stats}. 
             Format JSON STRICT : {{\"summary\": \"...\", \"risks\": \"...\", \"recommendations\": \"...\"}}.
             Répond en français, tu marqueras les texte important en gras sans utiliser
             les balises HTML et ton analyse ne doit pas etre court ni etre long.
             NE PAS exporter autre chose que du JSON."""
            response = model.generate_content(prompt)
            
            clean_text = response.text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
                
            return clean_text
    except Exception as e:
        print(f"Erreur API IA: {e}")
    
    fallback_summary = f"Analyse de Performance : La promotion affiche une moyenne de {stats['moyenne_generale']}/20. La répartition des notes indique une structure de classe stable mais perfectible."
    fallback_risks = f"Points de vigilance : Avec une participation moyenne de {stats['participation_moyenne']}%, certains étudiants risquent l'isolement académique. Les étudiants en dessous du seuil de 10/20 doivent être identifiés."
    fallback_recs = (
        "Stratégie de Soutien : Mettre en place des groupes de tutorat pour les filières en difficulté."
        "Optimisation : Augmenter l'interactivité durant les cours pour booster la participation."
        "Suivi : Entretiens individuels pour les étudiants avec un temps d'étude inférieur à la moyenne."
    )
    
    return json.dumps({
        "summary": fallback_summary,
        "risks": fallback_risks,
        "recommendations": fallback_recs
    })

@app.route('/add', methods=["POST"])
def add_student():
    """ Ajoute un nouvel étudiant et redirige vers les résultats """
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    sexe = request.form["sexe"]
    ville = request.form["ville"]
    niveau = request.form["niveau"]
    filiere = request.form["filiere"]
    moyenne = float(request.form["moyenne"].replace(',', '.'))
    temps = float(request.form["temps_etude"].replace(',', '.'))
    age = int(request.form["age"])
    participation = int(request.form["participation"])
    sommeil = float(request.form.get("sommeil", 7.0))
    distraction = request.form.get("distraction", "Aucune")

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO students (nom, prenom, sexe, ville, niveau, filiere, moyenne, temps, age, participation, sommeil, distraction) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nom, prenom, sexe, ville, niveau, filiere, moyenne, temps, age, participation, sommeil, distraction))
    student_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return redirect(url_for('analyse_personnelle', id=student_id))

@app.route('/update/<int:id>', methods=["POST"])
def update_student(id):
    """ Met à jour l'étudiant N° id puis redirige vers résultats """
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    sexe = request.form["sexe"]
    ville = request.form["ville"]
    niveau = request.form["niveau"]
    filiere = request.form["filiere"]
    moyenne = float(request.form["moyenne"].replace(',', '.'))
    temps = float(request.form["temps_etude"].replace(',', '.'))
    age = int(request.form["age"])
    participation = int(request.form["participation"])
    sommeil = float(request.form.get("sommeil", 7.0))
    distraction = request.form.get("distraction", "Aucune")

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE students
        SET nom=?, prenom=?, sexe=?, ville=?, niveau=?, filiere=?, moyenne=?, temps=?, age=?, participation=?, sommeil=?, distraction=?
        WHERE id=?
    ''', (nom, prenom, sexe, ville, niveau, filiere, moyenne, temps, age, participation, sommeil, distraction, id))
    conn.commit()
    conn.close()

    return redirect(url_for('analyse_personnelle', id=id))

@app.route('/delete/<int:id>')
def delete_student(id):
    """ Supprime l'étudiant via son ID puis redirige vers résultats """
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('resultats'))

def keep_alive():
    def ping_loop():
        while True:
            try:
                url = os.environ.get(
                    "RENDER_EXTERNAL_URL",
                    "https://bot-telegram-krsa.onrender.com"
                )
                requests.get(url, timeout=10)
                print("Ping Render OK")
            except Exception as e:
                print(f"Ping échoué : {e}")
            time.sleep(600)

    t = threading.Thread(target=ping_loop)
    t.daemon = True
    t.start()

@app.route('/scrapper', methods=["POST"])
def scrapper():
    # On récupère les critères du formulaire
    pays = request.form.get("pays", "Cameroun")
    ville = request.form.get("ville", "Yaoundé")
    filiere = request.form.get("filiere", "Informatique")
    niveau = request.form.get("niveau", "Licence")
    
    # On définit une URL par défaut car le formulaire n'en demande pas
    url_cible = f"https://fr.wikipedia.org/wiki/{filiere}"
        
    try:
        if SCRAPING_API_KEY and SCRAPING_API_KEY != "VOTRE_CLE_SCRAPING":
            api_url = f"https://api.scrapingant.com/v2/general?url={url_cible}&x-api-key={SCRAPING_API_KEY}"
            response = requests.get(api_url, timeout=15)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    html_content = data.get('content', '')
                except ValueError:
                    html_content = response.text
            else:
                print(f"Erreur ScrapingAnt {response.status_code}: {response.text}")
                fallback_response = requests.get(url_cible, timeout=10)
                html_content = fallback_response.text
        else:
            # Simulation sans clé API
            response = requests.get(url_cible, timeout=10)
            html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')
        
        prenoms = [
            "Jean", "Marie", "Alain", "Sophie", "Paul", "Alice", "Yann", "Aminata", "Koffi", "Fatou",
            "Kengne", "Emilie", "Claude", "Mendy", "Djengue", "Landry", "Marc", "Luc", "Julie", "Sarah",
            "Moussa", "Awa", "Ibrahim", "Oumar", "Amadou", "Binta", "Claire", "Thomas", "Pierre", "Laura",
            "Emma", "Julien", "Antoine", "Camille", "Hugo", "Lea", "Nadine", "Sylvie", "Bernard", "Michel",
            "Serge", "Chantal", "David", "Anne", "Nicolas", "Sandrine", "Cedric", "Thierry", "Karim", "Ali",
            "Samira", "Fatima", "Emmanuel", "Grace", "Christelle"
        ]
        noms = [
            "Dupont", "Traoré", "Kamga", "Müller", "Smith", "Nguyen", "Diallo", "Zongo", "Moukourou", "Etoundi",
            "Bavoui", "Etoa", "Momo", "Tchami", "Ekani", "Tchakui", "Soh", "Martin", "Bernard", "Thomas",
            "Petit", "Robert", "Richard", "Durand", "Dubois", "Moreau", "Laurent", "Simon", "Michel", "Lefebvre",
            "Leroy", "Roux", "David", "Bertrand", "Morel", "Fournier", "Girard", "Bonnet", "Garnier", "Ndiaye",
            "Diop", "Fall", "Sarr", "Sy", "Gueye", "Cisse", "Toure", "Kone", "Keita", "Diarra", "Fofana",
            "Coulibaly", "Owona", "Belinga", "Fouda"
        ]
        
        new_students = []
        for _ in range(5):
            s = (
                random.choice(noms), 
                random.choice(prenoms), 
                random.choice(["Homme", "Femme"]), 
                ville, 
                niveau, 
                filiere, 
                round(random.uniform(10, 19), 2), # Moyenne
                random.randint(5, 25),            # Temps étude
                random.randint(18, 30),           # Age
                random.randint(40, 80),           # Participation
                round(random.uniform(4, 9), 1),   # Sommeil
                random.choice(["Réseaux sociaux", "Jeux vidéo", "Séries/Films", "Sorties", "Aucune"]) # Distraction
            )
            new_students.append(s)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        for s in new_students:
            cursor.execute('''
                INSERT INTO students (nom, prenom, sexe, ville, niveau, filiere, moyenne, temps, age, participation, sommeil, distraction) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', s)
        conn.commit()
        conn.close()
        
        return redirect(url_for('resultats'))
    except Exception as e:
        print(f"Erreur Scrapping: {e}")
        return f"Erreur lors de l'extraction : {e}. Vérifiez votre clé API dans le fichier .env"

@app.route('/analyse_personnelle/<int:id>')
def analyse_personnelle(id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return redirect(url_for('resultats'))
        
    student = {
        'id': row[0], 'nom': row[1], 'prenom': row[2], 'sexe': row[3],
        'ville': row[4], 'niveau': row[5], 'filiere': row[6],
        'moyenne': row[7], 'temps': row[8], 'age': row[9],
        'participation': row[10], 
        'sommeil': row[11] if len(row) > 11 else 7.0,
        'distraction': row[12] if len(row) > 12 else 'Aucune'
    }
    return render_template('analyse_personnelle.html', student=student)

@app.route('/api/analyse_personnelle/<int:id>')
def api_analyse_personnelle(id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return json.dumps({"erreur": "Étudiant introuvable"})
        
    student = {
        'prenom': row[2], 'filiere': row[6], 'moyenne': row[7],
        'temps': row[8], 'participation': row[10], 
        'sommeil': row[11] if len(row) > 11 else 7.0,
        'distraction': row[12] if len(row) > 12 else 'Aucune'
    }
    
    try:
        api_key = key_rotation()
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"""
            Tu es un coach étudiant bienveillant. 
            Voici les données d'un étudiant : {student}.
            Fais une analyse PERSONNELLE très courte, encourageante et donne des conseils pratiques (ex: nutrition, sommeil, gestion du temps, méthodes de travail liées à sa filière et ses distractions).
            Format JSON STRICT: {{"analyse": "...", "conseils": ["conseil 1", "conseil 2", "conseil 3"]}}
            Ne renvoie que du JSON. Ne met pas les balises ```json.
            """
            response = model.generate_content(prompt)
            clean_text = response.text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            return clean_text
    except Exception as e:
        print(f"Erreur API IA Perso: {e}")
        
    # Fallback
    return json.dumps({
        "analyse": f"Bonjour {student['prenom']} ! Tes habitudes montrent que tu travailles dur, mais n'oublie pas l'équilibre.",
        "conseils": [
            "Assure-toi de dormir au moins 7 à 8 heures par nuit.",
            "Consomme des fruits comme la banane ou la pomme pour garder ton énergie.",
            f"Fais attention à tes distractions comme '{student['distraction']}'. Fixe-toi des limites !"
        ]
    })

init_db()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
    keep_alive()
