from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class Nutritionist(Base):
    __tablename__ = "nutritionist"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone_number = Column(String, unique=True, index=True)
    whatsapp_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    clients = relationship("Client", back_populates="nutritionist")


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True, index=True)
    nutritionist_id = Column(Integer, ForeignKey("nutritionist.id"))
    name = Column(String, index=True)
    phone_number = Column(String, unique=True, index=True)
    
    target_calories = Column(Float, nullable=True)
    target_protein_g = Column(Float, nullable=True)
    target_carbs_g = Column(Float, nullable=True)
    target_fat_g = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    nutritionist = relationship("Nutritionist", back_populates="clients")
    meal_logs = relationship("MealLog", back_populates="client")
    weekly_reports = relationship("WeeklyReport", back_populates="client")


class MealLog(Base):
    __tablename__ = "meal_log"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client.id"))
    logged_at = Column(DateTime, default=datetime.utcnow)
    
    raw_message = Column(String, nullable=True)
    parsed_meals = Column(JSON, nullable=True)
    
    total_calories = Column(Float, nullable=True)
    total_protein_g = Column(Float, nullable=True)
    total_carbs_g = Column(Float, nullable=True)
    total_fat_g = Column(Float, nullable=True)
    
    workout_notes = Column(String, nullable=True)
    weight_kg = Column(Float, nullable=True)

    client = relationship("Client", back_populates="meal_logs")


class WeeklyReport(Base):
    __tablename__ = "weekly_report"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client.id"))
    week_start = Column(DateTime)
    week_end = Column(DateTime)
    
    avg_calories = Column(Float, nullable=True)
    avg_protein = Column(Float, nullable=True)
    compliance_score = Column(Float, nullable=True)
    
    report_pdf_url = Column(String, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="weekly_reports")
