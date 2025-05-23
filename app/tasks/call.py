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

# Define offer texts for upsell calls
OFFERS = {
    'WaitlistUsers': (
        "Order the base package now, and only pay 195 to get a 4 year subscription! "
    ),
    'myAIAgentsUser': (
        "Buy value pack now, and we'll quadruple its value on release! "
        "Which means, when you buy 100 euro now, we'll give you 400 euro when going live. "
    ),
}

# Thank-you message
THANK_YOU_MESSAGE = "Thank you for signing up! We're excited to have you on board. Let us know if you need any help!"

# Thresholds
UPSELL_THRESHOLD = (
    datetime.timedelta(seconds=10) if settings.DEBUG else datetime.timedelta(days=5)
)
THANK_YOU_CALL_THRESHOLD = datetime.timedelta(minutes=15)

async def run_call_job():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    logger.info(f"[{now_utc.isoformat()}] Running Job: Fetch clients and process calls...")

    db_url = settings.MONGO_DB_URL
    db_name = settings.MONGO_DATABASE_NAME
    waitlist_service = MongoService(db_url, db_name, 'WaitlistUsers')
    agents_service   = MongoService(db_url, db_name, 'myAIAgentsUser')

    try:
        for coll_name, collection in [
            ('WaitlistUsers', waitlist_service._get_collection()),
            ('myAIAgentsUser', agents_service._get_collection()),
        ]:
            logger.debug(f"Processing collection: {coll_name}")
            for client in collection.find({}):
                doc_id = client.get('_id')
                name = client.get('fullName')
                phone = client.get('phoneNumber')
                language = client.get('language')
                created = client.get('createdAt')

                if not (name and phone and language and created):
                    logger.info(f"Skipping {coll_name} {doc_id}: missing fields")
                    continue

                # Parse createdAt
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

                # Assume Europe/Bucharest if naive
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=ZoneInfo('Europe/Bucharest'))

                created_utc = created_dt.astimezone(datetime.timezone.utc)
                age = now_utc - created_utc
                logger.debug(f"Doc {doc_id} age = {age}")

                n_calls = client.get('n_calls', 0)
                call_history = client.get('call_history', [])
                offer = OFFERS.get(coll_name, "")

                # === UPSALE CALL ===
                if n_calls == 0 and age >= UPSELL_THRESHOLD:
                    logger.info(f"Initiating UPSALE call for {coll_name} {doc_id} ({name})")
                    if settings.DEBUG:
                        phone = "+40785487261"

                    payload = {'phone': phone, 'name': name, 'language': language, 'offer': offer}
                    resp = await send_phone_call_request(payload)

                    if resp and 'id' in resp:
                        call_id = resp['id']
                        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        collection.update_one(
                            {'_id': doc_id},
                            {
                                '$push': {'call_history': {
                                    'call_id': call_id,
                                    'timestamp': timestamp,
                                    'type': 'upsell'
                                }},
                                '$inc': {'n_calls': 1}
                            }
                        )
                        logger.info(f"Recorded UPSALE call {call_id} @ {timestamp}")
                        await asyncio.sleep(30)
                    else:
                        logger.info(f"Failed to initiate UPSALE call for {doc_id}: {resp}")

                # === THANK-YOU CALL ===
                elif n_calls == 1 and age >= THANK_YOU_CALL_THRESHOLD:
                    has_thankyou_call = any(c.get('type') == 'thankyou' for c in call_history)
                    if not has_thankyou_call:
                        logger.info(f"Initiating THANK-YOU call for {coll_name} {doc_id} ({name})")
                        if settings.DEBUG:
                            phone = "+40785487261"

                        payload = {'phone': phone, 'name': name, 'language': language, 'offer': THANK_YOU_MESSAGE}
                        resp = await send_phone_call_request(payload)

                        if resp and 'id' in resp:
                            call_id = resp['id']
                            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                            collection.update_one(
                                {'_id': doc_id},
                                {
                                    '$push': {'call_history': {
                                        'call_id': call_id,
                                        'timestamp': timestamp,
                                        'type': 'thankyou'
                                    }},
                                    '$inc': {'n_calls': 1}
                                }
                            )
                            logger.info(f"Recorded THANK-YOU call {call_id} @ {timestamp}")
                            await asyncio.sleep(30)
                        else:
                            logger.info(f"Failed to initiate THANK-YOU call for {doc_id}: {resp}")

                # === PENDING CALLS CHECK ===
                else:
                    logger.debug("Checking pending calls...")
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
