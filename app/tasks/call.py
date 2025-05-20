import asyncio
import datetime
from zoneinfo import ZoneInfo
from pymongo.collection import Collection
from app.services.vapi_service import send_phone_call_request, check_call_status
from app.services.mongo_service import MongoService
from app.core.config import settings
import logging

# Set up the logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define offer texts for each source
OFFERS = {
    'WaitlistUsers': (
        "Order the base package now, and only pay 195 to get a 4 year subscription! "
    ),
    'myAIAgentsUser': (
        "Buy value pack now, and we'll quadruple its value on release! "
        "Which means, when you buy 100 euro now, we'll give you 400 euro when going live. "
    ),
}

# Threshold for new calls
THRESHOLD = (
    datetime.timedelta(seconds=10)
    if settings.DEBUG
    else datetime.timedelta(days=5)
)

async def run_call_job():
    # Always compare against UTC “now”
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    logger.info(f"[{now_utc.isoformat()}] Running Job: Fetch clients and process calls...")

    # Mongo setup
    db_url = settings.MONGO_DB_URL
    db_name = settings.MONGO_DATABASE_NAME
    waitlist_service = MongoService(db_url, db_name, 'WaitlistUsers')
    agents_service   = MongoService(db_url, db_name, 'myAIAgentsUser')

    try:
        for coll_name, collection in [
            ('WaitlistUsers',   waitlist_service._get_collection()),
            ('myAIAgentsUser',  agents_service._get_collection()),
        ]:
            logger.debug(f"Processing collection: {coll_name}")
            for client in collection.find({}):
                doc_id    = client.get('_id')
                name      = client.get('fullName')
                phone     = client.get('phoneNumber')
                language  = client.get('language')
                created   = client.get('createdAt')

                # Must have the basics
                if not (name and phone and language and created):
                    logger.info(f"Skipping {coll_name} {doc_id}: missing fields")
                    continue

                # 1) Parse createdAt
                if isinstance(created, str):
                    try:
                        created_dt = datetime.datetime.fromisoformat(created)
                    except Exception:
                        logger.warning(f"Bad date for {doc_id}: {created}")
                        continue
                elif isinstance(created, datetime.datetime):
                    created_dt = created
                else:
                    logger.warning(f"Unexpected createdAt type for {doc_id}: {type(created)}")
                    continue

                # 2) If naive, assume Europe/Bucharest
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=ZoneInfo('Europe/Bucharest'))

                # 3) Convert to UTC
                created_utc = created_dt.astimezone(datetime.timezone.utc)

                # 4) Compute age
                age = now_utc - created_utc
                logger.debug(f"Doc {doc_id} age = {age} (threshold = {THRESHOLD})")

                # 5) Skip if too old
                print(age, THRESHOLD, age-THRESHOLD)
                if age < THRESHOLD:
                    logger.info(f"Skipping {coll_name} {doc_id}: created {age} ago")
                    continue

                n_calls      = client.get('n_calls', 0)
                call_history = client.get('call_history', [])
                offer        = OFFERS[coll_name]

                # First-time call
                if n_calls == 0:
                    logger.info(f"Initiating call for {coll_name} {doc_id} ({name})")
                    if settings.DEBUG:
                        phone = "+40785487261"

                    payload = {'phone': phone, 'name': name, 'language': language, 'offer': offer}
                    resp = await send_phone_call_request(payload)

                    if resp and 'id' in resp:
                        call_id   = resp['id']
                        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        collection.update_one(
                            {'_id': doc_id},
                            {
                                '$push': {'call_history': {'call_id': call_id, 'timestamp': timestamp}},
                                '$inc': {'n_calls': 1}
                            }
                        )
                        logger.info(f"Recorded call {call_id} @ {timestamp}")
                        await asyncio.sleep(30)
                    else:
                        logger.info(f"Failed to initiate call for {doc_id}: {resp}")

                # Check pending
                else:
                    print("Checking pending calls...")
                    pending = [e for e in call_history if 'response' not in e]
                    for entry in pending:
                        cid = entry['call_id']
                        logger.info(f"Checking status for call {cid}")
                        status = await check_call_status(cid)
                        if status and status.get('status') == 'ended':
                            collection.update_one(
                                {'_id': doc_id},
                                {'$set': {'call_history.$[e].response': status}},
                                array_filters=[{'e.call_id': cid, 'e.response': {'$exists': False}}]
                            )
                            logger.info(f"Saved response for call {cid}")
                        else:
                            logger.info(f"Call {cid} not ended or error: {status}")

        logger.info("Call job completed.")

    finally:
        waitlist_service.close_connection()
        agents_service.close_connection()

if __name__ == "__main__":
    asyncio.run(run_call_job())
