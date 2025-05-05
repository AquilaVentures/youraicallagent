# app/utils/data_fetcher.py
import logging
import httpx
import asyncio
import json
from typing import Optional, Dict, Any, List, Union
from app.core.config import settings

# Set up the logger
# Consider configuring logging more centrally in main.py or a dedicated logging module later
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataFetcher:
    """
    A simple class to asynchronously fetch data from a given URL.
    """

    def __init__(self, url: str):
        """
        Initializes the DataFetcher with the URL to fetch data from.

        Args:
            url: The URL string to fetch data from.
        """
        if not url:
            raise ValueError("URL cannot be empty")
        self.url = url
        logger.info(f"DataFetcher initialized for URL: {self.url}")

    async def fetch_data(self) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """
        Asynchronously fetches data from the initialized URL.

        Attempts to parse the response as JSON.

        Returns:
            The fetched data as a dictionary or list if the response is JSON
            and the request was successful (status 200), otherwise None.
        """
        logger.info(f"Attempting to fetch data from: {self.url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.url)
                response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

                if response.status_code == 200:
                    logger.info(f"Successfully fetched data from {self.url}")
                    try:
                        # Attempt to parse the response body as JSON
                        data = response.json()
                        logger.debug("Response parsed as JSON.")
                        return data
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode JSON from response for {self.url}. Response body: {response.text[:200]}...") # Log first 200 chars
                        return None
                else:
                    # This part might not be reached if raise_for_status() handles it,
                    # but kept for clarity.
                    logger.warning(f"Received unexpected status code {response.status_code} from {self.url}: {response.text}")
                    return None
            except httpx.RequestError as exc:
                logger.error(f"HTTP Request Error occurred while fetching from {self.url}: {exc}")
                return None
            except httpx.HTTPStatusError as exc:
                logger.error(f"HTTP Status Error occurred while fetching from {self.url}: Status {exc.response.status_code}, Response: {exc.response.text}")
                # You might want to return the partial response or specific error info here
                # depending on how you want to handle different errors
                return None
            except Exception as exc:
                logger.error(f"An unexpected error occurred during fetch_data: {exc}")
                return None

# --- Main execution block for testing ---
async def main_test():
    """Main function to test the DataFetcher class when run directly."""
    logger.info("--- Starting DataFetcher Test ---")

    # Use the URL from settings
    data_url = settings.DATA_SOURCE_URL

    if not data_url or data_url == "YOUR_DATA_SOURCE_URL":
         logger.error("settings.DATA_SOURCE_URL is not configured. Please set it to a valid URL for testing.")
         logger.info("--- DataFetcher Test Finished (Configuration Error) ---")
         return


    # Create an instance of the DataFetcher
    fetcher = DataFetcher(data_url)

    # Fetch the data
    fetched_data = await fetcher.fetch_data()

    # Print the result
    if fetched_data is not None:
        logger.info("Data fetched successfully:")
        # Use json.dumps for pretty printing the JSON object
        print(json.dumps(fetched_data, indent=2))
    else:
        logger.warning("Failed to fetch data.")

    logger.info("--- DataFetcher Test Finished ---")


if __name__ == "__main__":
    asyncio.run(main_test())

