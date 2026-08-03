import mysql.connector
from mysql.connector import Error
from fastapi import HTTPException
import random

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  
    "database": "angovo_db"
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Erreur de connexion BDD : {str(e)}")

def verifier_email_existe(email: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_user FROM users WHERE email = %s", (email,))
    existe = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return existe

def inserer_nouvel_utilisateur(user, hashed_password: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Insertion dans la table 'users'
        query_user = """
            INSERT INTO users (nom, prenom, email, password_hash, telephone, date_naissance, ville, quartier, adresse_exacte, plan_actuel) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            VALUES (%s, %s, %s, %s, %s, 'Actif')
        """
        cursor.execute(query_compteur, (
            id_user, user.num_compteur, id_client_police, 
            user.type_abonnement, user.choix_kwh_base
        ))
        id_compteur = cursor.lastrowid
        
        # 3. Insertion de l'historique par défaut
        historique_donnees = [('Mar', 165, 2026), ('Avr', 210, 2026), ('Mai', 187, 2026)]
        query_histo = "INSERT INTO consommations_historique (id_compteur, label_mois, valeur_kwh, annee) VALUES (%s, %s, %s, %s)"
        for mois, valeur, annee in historique_donnees:
            cursor.execute(query_histo, (id_compteur, mois, valeur, annee))
            
        # 4. Insertion d'une première facture non payée
        query_facture = """
            INSERT INTO factures (id_compteur, reference_facture, periode_mois, consommation_kwh, montant_mga, statut_paiement, date_echeance) 
            VALUES (%s, %s, %s, %s, %s, 'non_payee', '2026-05-31')
        """
        ref_facture = f"JIR-2026-{random.randint(10000, 99999)}"
        cursor.execute(query_facture, (id_compteur, ref_facture, "Mai 2026", 187, 48200.00))

        conn.commit()
        return id_user
    except mysql.connector.Error as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur SQL : {str(err)}")
    finally:
        cursor.close()
        conn.close()

def recuperer_utilisateur_par_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def recuperer_donnees_dashboard(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query_profile = """
        SELECT u.nom, u.prenom, u.email, u.telephone, u.date_naissance, u.ville, u.quartier, 
               u.adresse_exacte as adresse, u.plan_actuel as plan, 
               c.id_compteur, c.num_compteur, c.id_client_police as id_client, c.type_abonnement
        FROM users u
        LEFT JOIN compteurs c ON u.id_user = c.id_user
        WHERE u.id_user = %s
    """
    cursor.execute(query_profile, (user_id,))
    profile_data = cursor.fetchone()
    
    if not profile_data:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
        
    id_compteur = profile_data.get("id_compteur")
    factures = []
    historique_conso = []
    
    if id_compteur:
        cursor.execute("SELECT id_facture as id, reference_facture, periode_mois as mois, consommation_kwh as kwh, montant_mga as montant, statut_paiement as statut, date_echeance FROM factures WHERE id_compteur = %s ORDER BY id_facture DESC", (id_compteur,))
        factures = cursor.fetchall()
        
        cursor.execute("SELECT label_mois, valeur_kwh FROM consommations_historique WHERE id_compteur = %s ORDER BY id_conso ASC", (id_compteur,))
        historique_conso = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return {"userProfile": profile_data, "factures": factures, "historiqueConso": historique_conso}

def mettre_a_jour_paiement_facture(facture_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("UPDATE factures SET statut_paiement = 'payee', date_paiement = NOW() WHERE id_facture = %s", (facture_id,))
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        conn.close()