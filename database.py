import sqlite3
from fastapi import HTTPException
import random
import os

# Fichier SQLite local (il se créera tout seul sur le serveur)
DB_NAME = "angovo.db"

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_NAME)
        # Permet de récupérer les résultats sous forme de dictionnaire
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de connexion BDD : {str(e)}")

def verifier_email_existe(email: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_user FROM users WHERE email = ?", (email,))
    existe = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return existe

def inserer_nouvel_utilisateur(user, hashed_password: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Insertion dans la table 'users'
        query_user = """
            INSERT INTO users (nom, prenom, email, password_hash, telephone, date_naissance, ville, quartier, adresse_exacte, plan_actuel) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        plan = user.plan if user.plan in ['Gratuit', 'Premium'] else 'Gratuit'
        cursor.execute(query_user, (
            user.nom, user.prenom, user.email, hashed_password, 
            user.telephone, user.date_naissance, user.ville, user.quartier, 
            user.adresse_exacte, plan
        ))
        id_user = cursor.lastrowid
        
        # 2. Insertion automatique dans la table 'compteurs'
        id_client_police = f"{random.randint(200,299)}-{random.randint(400,499)}-{random.randint(800,899)}"
        query_compteur = """
            INSERT INTO compteurs (id_user, num_compteur, id_client_police, type_abonnement, choix_kwh_base, statut_compteur) 
            VALUES (?, ?, ?, ?, ?, 'Actif')
        """
        cursor.execute(query_compteur, (
            id_user, user.num_compteur, id_client_police, 
            user.type_abonnement, user.choix_kwh_base
        ))
        id_compteur = cursor.lastrowid
        
        # 3. Insertion de l'historique par défaut
        historique_donnees = [('Mar', 165, 2026), ('Avr', 210, 2026), ('Mai', 187, 2026)]
        query_histo = "INSERT INTO consommations_historique (id_compteur, label_mois, valeur_kwh, annee) VALUES (?, ?, ?, ?)"
        for mois, valeur, annee in historique_donnees:
            cursor.execute(query_histo, (id_compteur, mois, valeur, annee))
            
        # 4. Insertion d'une première facture non payée
        query_facture = """
            INSERT INTO factures (id_compteur, reference_facture, periode_mois, consommation_kwh, montant_mga, statut_paiement, date_echeance) 
            VALUES (?, ?, ?, ?, ?, 'non_payee', '2026-05-31')
        """
        ref_facture = f"JIR-2026-{random.randint(10000, 99999)}"
        cursor.execute(query_facture, (id_compteur, ref_facture, "Mai 2026", 187, 48200.00))

        conn.commit()
        return id_user
    except Exception as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur SQL : {str(err)}")
    finally:
        cursor.close()
        conn.close()

def recuperer_utilisateur_par_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(user) if user else None

def recuperer_donnees_dashboard(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query_profile = """
        SELECT u.nom, u.prenom, u.email, u.telephone, u.date_naissance, u.ville, u.quartier, 
               u.adresse_exacte as adresse, u.plan_actuel as plan, 
               c.id_compteur, c.num_compteur, c.id_client_police as id_client, c.type_abonnement
        FROM users u
        LEFT JOIN compteurs c ON u.id_user = c.id_user
        WHERE u.id_user = ?
    """
    cursor.execute(query_profile, (user_id,))
    profile_data = cursor.fetchone()
    
    if not profile_data:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
        
    profile_dict = dict(profile_data)
    id_compteur = profile_dict.get("id_compteur")
    factures = []
    historique_conso = []
    
    if id_compteur:
        cursor.execute("SELECT id_facture as id, reference_facture, periode_mois as mois, consommation_kwh as kwh, montant_mga as montant, statut_paiement as statut, date_echeance FROM factures WHERE id_compteur = ? ORDER BY id_facture DESC", (id_compteur,))
        factures = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT label_mois, valeur_kwh FROM consommations_historique WHERE id_compteur = ? ORDER BY id_conso ASC", (id_compteur,))
        historique_conso = [dict(row) for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    return {"userProfile": profile_dict, "factures": factures, "historiqueConso": historique_conso}

def mettre_a_jour_paiement_facture(facture_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE factures SET statut_paiement = 'payee', date_paiement = CURRENT_TIMESTAMP WHERE id_facture = ?", (facture_id,))
        conn.commit()
    except Exception as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        conn.close()


def initialiser_base_de_donnees():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table des utilisateurs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id_user INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            prenom TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            telephone TEXT,
            date_naissance TEXT,
            ville TEXT,
            quartier TEXT,
            adresse_exacte TEXT,
            plan_actuel TEXT
        )
    """)
    
    # Table des compteurs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compteurs (
            id_compteur INTEGER PRIMARY KEY AUTOINCREMENT,
            id_user INTEGER,
            num_compteur TEXT,
            id_client_police TEXT,
            type_abonnement TEXT,
            choix_kwh_base INTEGER,
            statut_compteur TEXT,
            FOREIGN KEY (id_user) REFERENCES users (id_user)
        )
    """)
    
    # Table de l'historique de consommation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consommations_historique (
            id_conso INTEGER PRIMARY KEY AUTOINCREMENT,
            id_compteur INTEGER,
            label_mois TEXT,
            valeur_kwh INTEGER,
            annee INTEGER,
            FOREIGN KEY (id_compteur) REFERENCES compteurs (id_compteur)
        )
    """)
    
    # Table des factures
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS factures (
            id_facture INTEGER PRIMARY KEY AUTOINCREMENT,
            id_compteur INTEGER,
            reference_facture TEXT,
            periode_mois TEXT,
            consommation_kwh INTEGER,
            montant_mga REAL,
            statut_paiement TEXT,
            date_echeance TEXT,
            date_paiement TEXT,
            FOREIGN KEY (id_compteur) REFERENCES compteurs (id_compteur)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

# Exécuter l'initialisation dès l'importation du module
initialiser_base_de_donnees()