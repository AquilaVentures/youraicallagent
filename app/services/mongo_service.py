# app/services/mongo_service.py
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from typing import Optional, Dict, Any, List
from app.core.config import settings
import asyncio
import datetime

# Set up the logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s ' \
                    '- %(message)s')
logger = logging.getLogger(__name__)

class MongoService:
    """
    A service class for interacting with MongoDB.
    Handles connection, checking for existing documents, and saving documents.
    """

    def __init__(self, db_url: str, db_name: str, collection_name: str):
        """
        Initializes the MongoService.

        Args:
            db_url: The MongoDB connection URL.
            db_name: The name of the database to connect to.
            collection_name: The name of the collection to use.
        """
        if not db_url:
            raise ValueError("MongoDB URL cannot be empty")
        if not db_name:
            raise ValueError("MongoDB database name cannot be empty")
        if not collection_name:
            raise ValueError("MongoDB collection name cannot be empty")

        self.db_url = db_url
        self.db_name = db_name
        self.collection_name = collection_name
        self._client: Optional[MongoClient] = None
        self._db = None
        self._collection = None

        logger.info(f"MongoService initialized for DB: {db_name}, Collection: {collection_name}")

    def _connect(self):
        """Establishes the connection to MongoDB."""
        if self._client is None:
            try:
                # Connect to MongoDB
                self._client = MongoClient(self.db_url)
                # The ismaster command is cheap and does not require auth.
                self._client.admin.command('ismaster')
                self._db = self._client[self.db_name]
                self._collection = self._db[self.collection_name]
                logger.info("Successfully connected to MongoDB.")
            except ConnectionFailure as e:
                logger.error(f"Could not connect to MongoDB: {e}")
                self._client = None # Ensure client is None on failure
                raise # Re-raise the exception to signal failure
            except Exception as e:
                 logger.error(f"An unexpected error occurred during MongoDB connection: {e}")
                 self._client = None # Ensure client is None on failure
                 raise # Re-raise the exception

    def _get_collection(self):
        """Gets the MongoDB collection, ensuring connection is established."""
        if self._collection is None:
            self._connect() # Attempt to connect if not already connected
        return self._collection

    def close_connection(self):
        """Closes the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._collection = None
            logger.info("MongoDB connection closed.")

    def document_exists(self, doc_id: str) -> bool:
        """
        Checks if a document with the given _id exists in the collection.

        Args:
            doc_id: The _id of the document to check.

        Returns:
            True if the document exists, False otherwise.
        """
        collection = self._get_collection()
        if collection is None:
            logger.error("Cannot check document existence: MongoDB connection failed.")
            return False # Cannot check if connection failed

        try:
            # Find one document with the specified _id
            doc = collection.find_one({"_id": doc_id})
            return doc is not None
        except OperationFailure as e:
            logger.error(f"MongoDB Operation Failure while checking document existence for _id {doc_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred while checking document existence for _id {doc_id}: {e}")
            return False

    def save_document(self, document: Dict[str, Any]) -> Optional[str]:
        """
        Saves a single document to the collection.

        Args:
            document: The dictionary representing the document to save.
                      Assumes the document contains an '_id' field.

        Returns:
            The _id of the saved document if successful, otherwise None.
        """
        collection = self._get_collection()
        if collection is None:
            logger.error("Cannot save document: MongoDB connection failed.")
            return None # Cannot save if connection failed

        if '_id' not in document:
            logger.error("Document must contain an '_id' field to be saved.")
            return None

        try:
            # Insert the document. insert_one will raise DuplicateKeyError if _id exists,
            # but our logic in the calling script will prevent this if used correctly.
            # Using insert_one is generally preferred over upsert for clarity when
            # you specifically want to avoid duplicates based on a prior check.
            result = collection.insert_one(document)
            logger.info(f"Successfully saved document with _id: {result.inserted_id}")
            return str(result.inserted_id) # Return the inserted _id as a string
        except OperationFailure as e:
            logger.error(f"MongoDB Operation Failure while saving document with _id {document.get('_id')}: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving document with _id {document.get('_id')}: {e}")
            return None

# --- Main execution block for testing ---
# This block is for testing the MongoService class in isolation
async def main_mongo_test():
    """Main function to test the MongoService class when run directly."""
    logger.info("--- Starting MongoService Test ---")

    mongo_url = settings.MONGO_DB_URL
    db_name = getattr(settings, 'MONGO_DATABASE_NAME', 'earlybirds')
    collection_name = getattr(settings, 'MONGO_COLLECTION_NAME', 'fetched_clients')

    service = None # Initialize service to None
    try:
        # Create an instance of the MongoService
        service = MongoService(mongo_url, db_name, collection_name)

        # --- Test connection and basic operations ---
        # Create a dummy document for testing
        test_doc_id = "test_doc_12345"
        test_document = {
            "_id": test_doc_id,
            "message": "Hello from MongoService test!",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        # Test document_exists before saving
        exists_before = service.document_exists(test_doc_id)
        logger.info(f"Document with _id '{test_doc_id}' exists before saving: {exists_before}")

        # Test saving the document (only if it doesn't exist)
        if not exists_before:
            saved_id = service.save_document(test_document)
            if saved_id:
                logger.info(f"Test document saved successfully with _id: {saved_id}")
            else:
                logger.error("Failed to save test document.")
        else:
            logger.info(f"Test document with _id '{test_doc_id}' already exists. Skipping save.")

        # Test document_exists after saving (if it was saved)
        if not exists_before:
             exists_after = service.document_exists(test_doc_id)
             logger.info(f"Document with _id '{test_doc_id}' exists after saving: {exists_after}")

    except ValueError as e:
        logger.error(f"Initialization error: {e}")
    except ConnectionFailure:
        logger.error("Test aborted due to MongoDB connection failure.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during MongoService test: {e}")
    finally:
        # Ensure the connection is closed
        if service:
            service.close_connection()

    logger.info("--- MongoService Test Finished ---")


if __name__ == "__main__":
    # from dotenv import load_dotenv
    # load_dotenv()
    asyncio.run(main_mongo_test())

