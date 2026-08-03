from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

# Importation de nos modules logiques et algorithmiques
import security
import database

import os
import uvicorn

# --- INITIALISATION UNIQUE DE L'APPLICATION ---
app = FastAPI(
    title="Angovo API", 
    description="Architecture en couches de gestion énergétique"
)

# Configuration CORS pour la liaison Frontend-Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration des templates HTML (le dossier "templates" doit exister à la racine)
templates = Jinja2Templates(directory="templates")


# ==========================================
# 1. ROUTES FRONTEND (Affichage des pages HTML)
# ==========================================

@app.get("/")
def lire_accueil(request: Request):
    """Affiche automatiquement index.html à l'ouverture de l'URL principale"""
    return templates.TemplateResponse(request, "index.html", {})

@app.get("/connexion")
def page_connexion(request: Request):
    """Affiche la page de connexion"""
    return templates.TemplateResponse(request, "connexion.html", {})

@app.get("/inscription")
def page_inscription(request: Request):
    """Affiche la page de création de compte"""
    return templates.TemplateResponse(request, "inscription.html", {})


# ==========================================
# 2. MODÈLES PYDANTIC (Validation des données)
# ==========================================

class UserRegister(BaseModel):
    nom: str
    prenom: str
    email: EmailStr
    password: str
    telephone: str
    date_naissance: Optional[str] = None
    ville: str
    quartier: str
    adresse_exacte: str  
    num_compteur: str
    type_abonnement: str
    plan: str
    choix_kwh_base: Optional[int] = 0

    @field_validator('date_naissance', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        return None if (v == "" or v == "0000-00-00") else v

class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ==========================================
# 3. ROUTES API (Backend logique)
# ==========================================

@app.post("/api/register")
def register_user(user: UserRegister):
    security.valider_mot_de_passe_fort(user.password)
    
    if database.verifier_email_existe(user.email):
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")
        
    hashed = security.hacher_mot_de_passe(user.password)
    id_user = database.inserer_nouvel_utilisateur(user, hashed)
    
    return {"success": True, "message": "Utilisateur créé avec succès !", "user_id": id_user}

@app.post("/api/login")
def login_user(user: UserLogin):
    db_user = database.recuperer_utilisateur_par_email(user.email)
    
    if not db_user or not security.verifier_mot_de_passe(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
        
    return {"success": True, "message": "Connexion réussie !", "user_id": db_user["id_user"]}

@app.get("/api/dashboard/{user_id}")
def get_dashboard_data(user_id: int):
    try:
        return database.recuperer_donnees_dashboard(user_id)
    except HTTPException as he:
        if he.status_code == 404:
            return {
                "userProfile": {
                    "prenom": "Client",
                    "nom": "Angovo",
                    "email": "client@angovo.mg",
                    "plan_actuel": "Plan Standard",
                    "num_compteur": "457-JIR-MADA"
                },
                "factures": [],
                "historiqueConso": []
            }
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")

@app.post("/api/pay-facture/{facture_id}")
def pay_facture(facture_id: int):
    database.mettre_a_jour_paiement_facture(facture_id)
    return {"success": True, "message": "Facture réglée avec succès !"}


# ==========================================
# 4. LANCEMENT DU SERVEUR
# ==========================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)