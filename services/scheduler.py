import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db.database import SessionLocal
from db.models import Nutritionist
from agents.report_agent import run_report_agent
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def generate_weekly_reports():
    """Scheduled task to run every Sunday at 8am to generate reports."""
    logger.info("Starting weekly report generation for all nutritionists...")
    db = SessionLocal()
    try:
        nutritionists = db.query(Nutritionist).all()
        for nutritionist in nutritionists:
            await run_report_agent(nutritionist)
    except Exception as e:
        logger.error(f"Error during weekly report generation: {e}")
    finally:
        db.close()
    logger.info("Finished weekly report generation.")

def start_scheduler():
    logger.info("Starting APScheduler...")
    # Run every Sunday at 8:00 AM
    scheduler.add_job(generate_weekly_reports, 'cron', day_of_week='sun', hour=8, minute=0)
    scheduler.start()
