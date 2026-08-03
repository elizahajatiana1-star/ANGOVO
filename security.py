import re
from fastapi import HTTPException
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def valider_mot_de_passe_fort(password: str):
    """
    Algorithme de validation de mot de passe :
    - Au moins 8 caractères
    - Au moins une lettre majuscule
    - Au moins une lettre minuscule
    - Au moins un chiffre
    - Au moins un caractère spécial parmi @$!%*?&_
    """
    if len(password) < 8:
        raise HTTPException(
            status_code=400, 
            detail="Le mot de passe doit contenir au moins 8 caractères."
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=400, 
            detail="Le mot de passe doit contenir au moins une lettre majuscule."
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=400, 
            detail="Le mot de passe doit contenir au moins une lettre minuscule."
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=400, 
            detail="Le mot de passe doit contenir au moins un chiffre."
        )
    if not re.search(r"[@$!%*?&_#]", password):
        raise HTTPException(
            status_code=400, 
            detail="Le mot de passe doit contenir au moins un caractère spécial (@$!%*?&_#)."
        )

def hacher_mot_de_passe(password: str) -> str:
    return pwd_context.hash(password)

def verifier_mot_de_passe(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)