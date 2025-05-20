# app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.tasks.fetch import run_fetch_job
from app.tasks.call import run_call_job

# Set up the logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create the scheduler instance
scheduler = AsyncIOScheduler(timezone="UTC") # Use UTC for consistency

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for FastAPI lifespan events.
    Starts the scheduler on startup and shuts it down gracefully on shutdown.
    """
    print("Starting application and scheduler...")
    # # Job 1
    # scheduler.add_job(
    #     run_fetch_job,
    #     trigger=IntervalTrigger(seconds=10),
    #     id="fetch_job",
    #     name="Fetch Data",
    #     replace_existing=True,
    #     max_instances=1, # Ensure only one instance runs at a time
    #     coalesce=True    # Skip job run if previous one is still running
    # )

    # Job 2
    scheduler.add_job(
        run_call_job,
        trigger=IntervalTrigger(seconds=25),
        id="call_job",
        name="Launch VAPI Calls & Check Status of Previous Calls",
        replace_existing=True,
        max_instances=1, # Ensure only one instance runs at a time
        coalesce=True    # Skip job run if previous one is still running
    )

    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started.")
    try:
        yield # Application runs here
    finally:
        logger.info("Shutting down scheduler...")
        # Shut down the scheduler gracefully
        scheduler.shutdown()
        logger.info("Scheduler shut down.")
        logger.info("Application shutdown complete.")


# Create the FastAPI app instance with the lifespan context manager
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Basic root endpoint to check if the app is running
@app.get("/")
async def read_root():
    """
    Root endpoint providing a simple welcome message.
    """
    return {"message": f"Welcome to {settings.APP_NAME}"}

# --- Optional: Add API Routers here if needed ---
# from app.api import your_router
# app.include_router(your_router.router, prefix="/api/v1")

# Note: You don't need to explicitly run the app from here if using uvicorn.
# Uvicorn will import 'app' from this file.

