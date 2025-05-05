# app/tasks/call.py
import asyncio
import datetime
from pymongo.collection import Collection
from app.services.vapi_service import send_phone_call_request, check_call_status
from app.services.mongo_service import MongoService
from app.core.config import settings
import logging

# Set up the logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

async def run_call_job():
    """
    Fetch all clients, initiate calls for new clients,
    record call history, and check status for pending calls.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    logger.info(f"[{now}] Running Job: Fetch clients and process calls...")

    # Initialize the Mongo service
    db_url = settings.MONGO_DB_URL
    db_name = getattr(settings, 'MONGO_DATABASE_NAME', 'earlybirds')
    coll_name = getattr(settings, 'MONGO_COLLECTION_NAME', 'fetched_clients')
    mongo_service = MongoService(db_url, db_name, coll_name)

    try:
        # Get the raw PyMongo collection
        collection: Collection = mongo_service._get_collection()

        # 1. Fetch all client documents
        clients = list(collection.find({}))

        for client in clients:
            doc_id = client.get('_id')
            n_calls = client.get('n_calls', 0)
            call_history = client.get('call_history', [])

            # 2. If no calls have been made yet, initiate a new call
            if n_calls == 0:
                phone = client.get('phoneNumber')
                name = client.get('fullName')
                if not phone or not name:
                    logger.info(f"Skipping doc {doc_id}: missing phone or name")
                    continue

                logger.info(f"Initiating call for doc_id={doc_id} ({name} @ {phone})")

                # In DEBUG mode always call the test number
                if settings.DEBUG:
                    phone = "+40785487261"

                # Send the call request
                response = await send_phone_call_request({'phone': phone, 'name': name})

                if response and 'id' in response:
                    call_id = response['id']
                    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    # Push a new entry into call_history and increment n_calls
                    update_query = {
                        '$push': {
                            'call_history': {'call_id': call_id, 'timestamp': timestamp}
                        },
                        '$inc': {'n_calls': 1}
                    }
                    collection.update_one({'_id': doc_id}, update_query)
                    logger.info(f"Recorded new call in history for doc_id={doc_id}: {call_id} @ {timestamp}")

                    # Pause before next call
                    logger.info("Sleeping for 30 minutes to respect rate limits...")
                    await asyncio.sleep(30)
                else:
                    logger.info(f"Failed to initiate call for doc {doc_id}: {response}")

            # 3. If we’ve already made calls, check pending statuses
            else:
                # Iterate over history entries that lack a response
                pending_entries = [e for e in call_history if 'response' not in e]
                for entry in pending_entries:
                    entry_call_id = entry.get('call_id')
                    logger.info(f"Checking status for doc_id={doc_id}, call_id={entry_call_id}")
                    status_resp = await check_call_status(entry_call_id)

                    # Only update if call has ended
                    if status_resp and status_resp.get('status') == 'ended':
                        # Use arrayFilters to update only this history element
                        collection.update_one(
                            {'_id': doc_id},
                            {
                                '$set': { 'call_history.$[elem].response': status_resp }
                            },
                            array_filters=[{'elem.call_id': entry_call_id, 'elem.response': {'$exists': False}}]
                        )
                        logger.info(f"Saved response for doc_id={doc_id}, call_id={entry_call_id}")
                    else:
                        logger.info(f"Call not ended or error for doc_id={doc_id}, call_id={entry_call_id}: status={status_resp}")

        logger.info("Call job completed.")

    finally:
        # Ensure the Mongo connection is always closed
        mongo_service.close_connection()


if __name__ == "__main__":
    asyncio.run(run_call_job())
