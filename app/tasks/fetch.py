import asyncio
import datetime
from app.services.data_fetcher import DataFetcher
from app.core.config import settings
from app.services.mongo_service import MongoService
import logging

# Set up the logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

async def run_fetch_job():
    """
    Placeholder task for fetching data and calling VAPI.
    Currently just prints a message with a timestamp.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    logger.info(f"[{now}] Running Job 1: Fetching data and calling VAPI...")

    # Fetch the data
    fetcher = DataFetcher(settings.DATA_SOURCE_URL)
    fetched_data = await fetcher.fetch_data()

    logger.info(f"Fetched: {len(fetched_data)} items")

    # Save to mongoDB if not saved yet
    try:
        skipped_count = 0
        db_name = getattr(settings, 'MONGO_DATABASE_NAME', 'earlybirds')
        collection_name = getattr(settings, 'MONGO_COLLECTION_NAME', 'fetched_clients')
        mongo_service = MongoService(settings.MONGO_DB_URL, db_name, collection_name)
        # Iterate through fetched data and save if not exists
        for item in fetched_data:
            if not isinstance(item, dict):
                logger.warning(f"Skipping item as it is not a dictionary: {item}")
                continue

            item_id = item.get('_id')

            if not item_id:
                logger.warning(f"Skipping item as it does not have an '_id' field: {item}")
                continue

            # Check if the document already exists
            if mongo_service.document_exists(item_id):
                logger.debug(f"Item with _id '{item_id}' already exists. Skipping save.")
                skipped_count += 1
            else:
                # Save the document if it doesn't exist
                logger.debug(f"Item with _id '{item_id}' does not exist. Attempting to save.")

                # Set number of calls to 0
                item['n_calls'] = 0

                saved_id = mongo_service.save_document(item)
                logger.debug(f"Saved item with _id '{item_id}' to MongoDB.")
                if not saved_id:
                    logger.error(f"Failed to save item with _id '{item_id}'.")
    except Exception as e:
        logger.error(f"[{now}] An error occurred during MongoDB operations: {e}")
    finally:
        # Ensure the MongoDB connection is closed
        if mongo_service:
            mongo_service.close_connection()


if __name__ == "__main__":
    # For testing purposes, run the job directly
    asyncio.run(run_fetch_job())
