from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv(override=True)

from api.webhook import router as webhook_router
from services.scheduler import start_scheduler
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start the scheduler
    start_scheduler()
    yield
    # Shutdown logic goes here if needed

app = FastAPI(lifespan=lifespan)

app.include_router(webhook_router, tags=["webhook"])

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
