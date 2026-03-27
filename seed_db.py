import sys
import os
from datetime import datetime, timedelta

# Ensure the root directory is in the path
sys.path.insert(0, os.path.realpath(os.path.dirname(__file__)))

from db.database import SessionLocal
from db.models import Nutritionist, Client, MealLog

def seed():
    db = SessionLocal()

    print("Cleaning up old data...")
    db.query(MealLog).delete()
    db.query(Client).delete()
    db.query(Nutritionist).delete()
    db.commit()

    print("Inserting Nutritionists...")
    nutri1 = Nutritionist(
        name="Dr. Samar", 
        phone_number="+917987738993",
        whatsapp_number="+917987738993"
    )
    nutri2 = Nutritionist(
        name="Dr. Alex", 
        phone_number="+917217556581",
        whatsapp_number="+917217556581"
    )
    db.add_all([nutri1, nutri2])
    db.commit()
    db.refresh(nutri1)
    db.refresh(nutri2)

    print("Inserting Clients...")
    client1 = Client(
        nutritionist_id=nutri1.id,
        name="Alice",
        phone_number="+918450064622",
        target_calories=2000.0,
        target_protein_g=120.0,
        target_carbs_g=200.0,
        target_fat_g=60.0
    )
    
    client2 = Client(
        nutritionist_id=nutri2.id,
        name="Bob",
        phone_number="+917976061433",
        target_calories=2500.0,
        target_protein_g=150.0,
        target_carbs_g=250.0,
        target_fat_g=80.0
    )
    db.add_all([client1, client2])
    db.commit()
    db.refresh(client1)
    db.refresh(client2)

    print("Inserting Meal Logs...")
    logs = []
    
    # Client 1 Logs (Good day and Bad day)
    logs.append(MealLog(
        client_id=client1.id,
        logged_at=datetime.utcnow() - timedelta(days=1),
        raw_message="Had a salad and chicken breast",
        parsed_meals={"meals": [{"food": "salad", "calories": 300}, {"food": "chicken", "calories": 400}]},
        total_calories=1900.0,
        total_protein_g=110.0,
        total_carbs_g=180.0,
        total_fat_g=50.0,
        workout_notes="30 min run"
    ))
    logs.append(MealLog(
        client_id=client1.id,
        logged_at=datetime.utcnow() - timedelta(days=2),
        raw_message="Ate a whole pizza",
        parsed_meals={"meals": [{"food": "pizza", "calories": 2800}]},
        total_calories=2800.0,
        total_protein_g=90.0,
        total_carbs_g=300.0,
        total_fat_g=120.0
    ))

    # Client 2 Logs
    logs.append(MealLog(
        client_id=client2.id,
        logged_at=datetime.utcnow() - timedelta(days=1),
        raw_message="Steak and rice",
        parsed_meals={"meals": [{"food": "steak", "calories": 600}, {"food": "rice", "calories": 300}]},
        total_calories=2400.0,
        total_protein_g=140.0,
        total_carbs_g=240.0,
        total_fat_g=75.0,
        workout_notes="Heavy lifting"
    ))

    db.add_all(logs)
    db.commit()
    
    print(f"\n✅ Setup Complete!")
    print(f"Nutritionists:")
    print(f" - {nutri1.name} (Phone: {nutri1.phone_number}), ID: {nutri1.id}")
    print(f" - {nutri2.name} (Phone: {nutri2.phone_number}), ID: {nutri2.id}")
    print(f"\nClients:")
    print(f" - {client1.name} (Phone: {client1.phone_number}), ID: {client1.id} [Assigned to {nutri1.name}]")
    print(f" - {client2.name} (Phone: {client2.phone_number}), ID: {client2.id} [Assigned to {nutri2.name}]")
    print(f"\nTotal Logs inserted: {len(logs)}")
    db.close()

if __name__ == "__main__":
    seed()
