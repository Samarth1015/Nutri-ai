from sqlalchemy.orm import Session
from db.models import Nutritionist, Client
from utils.phone_utils import normalize_phone

def identify_sender(db: Session, phone: str):
    """Identify if the sender is a nutritionist or a client."""
    normalized = normalize_phone(phone)
    
    print(f"[Router] Normalizing phone: {phone} -> {normalized}")
    # Check nutritionists table first
    nutritionist = db.query(Nutritionist).filter(Nutritionist.phone_number == normalized).first()
    if nutritionist:
        return "nutritionist", nutritionist

    # Then check clients table
    client = db.query(Client).filter(Client.phone_number == normalized).first()
    if client:
        return "client", client

    return "unknown", None
