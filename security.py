from fastapi import HTTPException
import re

def valider_mot_de_passe_fort(password: str):
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 8 caractères.")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins une lettre majuscule.")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins une lettre minuscule.")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins un chiffre.")
    if not re.search(r"[@$!%*?&_#]", password):
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir un caractère spécial (@$!%*?&_#).")

def hacher_mot_de_passe(password: str) -> str:
    # On ne hache plus rien, on retourne le mot de passe tel quel
    return password

def verifier_mot_de_passe(plain_password: str, hashed_password: str) -> bool:
    # On compare simplement le texte brut entré avec celui de la base de données
    return plain_password == hashed_password