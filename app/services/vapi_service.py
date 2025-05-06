# app/services/vapi_service.py
import logging
import httpx # Use httpx for async requests
from typing import Optional, Dict, Any
import json
import asyncio

# Import settings from the core config
from app.core.config import settings
from dotenv import load_dotenv
load_dotenv(override=True)

# Set up the logger
# Consider configuring logging more centrally in main.py or a dedicated logging module later
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define global test variables
test_phone_number = "+40785487261"
test_last_name = "Bogdan"

print(json.dumps(settings.dict(), indent=2))

async def send_phone_call_request(
    params: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Asynchronously sends a POST request to the VAPI phone call endpoint.

    Args:
        params: A dictionary containing parameters for the call.
                Expected to include a 'phone' key for the customer number
                and other key-value pairs for assistantOverrides.variableValues.
                Example: {'phone': '+1234567890', 'name': 'John Doe', 'date': 'tomorrow'}

    Returns:
        A dictionary containing the JSON response from VAPI if successful (status 201),
        otherwise None.
    """
    if not settings.VAPI_API_KEY or not settings.VAPI_ASSISTANT_ID or not settings.VAPI_PHONE_NUMBER_ID:
        logger.error("VAPI configuration missing (token, assistant ID, or phone number ID). Cannot send call request.")
        return None

    if not isinstance(params, dict):
        logger.error("Invalid params type. Expected a dictionary.")
        return None

    customer_phone = params.get('phone')
    if not customer_phone:
        logger.error("Params dictionary must contain a 'phone' key with the customer number.")
        return None

    # Create the variableValues dictionary by copying params and removing the 'phone' key
    variable_values = params.copy()
    # if 'phone' in variable_values:
        # del variable_values['phone']
        
    # Optional: Add a check if variable_values is empty after removing phone,
    # depending on whether variableValues is mandatory for your assistant.
    # if not variable_values:
    #     logger.warning("No variableValues provided in params after removing 'phone'.")

    print(settings.VAPI_PHONE_NUMBER_ID)

    headers = {
        'Authorization': f'Bearer {settings.VAPI_API_KEY}',
        'Content-Type': 'application/json',
    }
    data = {
        'assistantId': settings.VAPI_ASSISTANT_ID,
        'phoneNumberId': settings.VAPI_PHONE_NUMBER_ID,
        'customer': {
            'number': customer_phone,
        },
        'assistantOverrides': {
            'variableValues': variable_values
        }
    }
    url = f"{settings.VAPI_BASE_URL}/call"

    logger.info(f"Attempting to send call request to {customer_phone} with variableValues: {variable_values}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

            if response.status_code == 201: # VAPI uses 201 Created for successful call initiation
                response_json = response.json()
                logger.info(f"Successfully initiated call to {customer_phone}. Call ID: {response_json.get('id')}")
                return response_json
            else:
                # This part might not be reached if raise_for_status() handles it,
                # but kept for clarity.
                logger.warning(f"Received unexpected status code {response.status_code} when initiating call to {customer_phone}: {response.text}")
                return None
        except httpx.RequestError as exc:
            logger.error(f"HTTP Request Error occurred while sending call request to {url}: {exc}")
            return None
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP Status Error occurred while sending call request to {url}: Status {exc.response.status_code}, Response: {exc.response.text}")
            # You might want to return the partial response or specific error info here
            # depending on how you want to handle different errors (e.g., 404 Not Found)
            try:
                 # Attempt to return the JSON response from the error body if available
                 return exc.response.json()
            except json.JSONDecodeError:
                 # If response body is not JSON, return a simple error indicator
                 return {"error": f"HTTP Status Error: {exc.response.status_code}", "detail": exc.response.text}
        except Exception as exc:
            logger.error(f"An unexpected error occurred during send_phone_call_request: {exc}")
            return None


async def check_call_status(call_id: str) -> Optional[Dict[str, Any]]:
    """
    Asynchronously checks the status of a specific VAPI call.

    Args:
        call_id: The ID of the call to check.

    Returns:
        A dictionary containing the call status JSON response if successful (status 200),
        otherwise None.
    """
    if not settings.VAPI_API_KEY:
        logger.error("VAPI Auth Token missing. Cannot check call status.")
        return None

    headers = {"Authorization": f'Bearer {settings.VAPI_API_KEY}'}
    url = f"{settings.VAPI_BASE_URL}/call/{call_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

            if response.status_code == 200:
                logger.debug(f"Successfully checked status for call_id {call_id}.")
                return response.json()
            else:
                # Might not be reached due to raise_for_status()
                logger.warning(f"Received unexpected status code {response.status_code} when checking status for call_id {call_id}: {response.text}")
                return None
        except httpx.RequestError as exc:
            logger.error(f"HTTP Request Error occurred while checking status for {url}: {exc}")
            return None
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP Status Error occurred while checking status for {url}: Status {exc.response.status_code}, Response: {exc.response.text}")
            # You might want to return the partial response or specific error info here
            # depending on how you want to handle different errors (e.g., 404 Not Found)
            try:
                 # Attempt to return the JSON response from the error body if available
                 return exc.response.json()
            except json.JSONDecodeError:
                 # If response body is not JSON, return a simple error indicator
                 return {"error": f"HTTP Status Error: {exc.response.status_code}", "detail": exc.response.text}
        except Exception as exc:
            logger.error(f"An unexpected error occurred during check_call_status: {exc}")
            return None

# --- Main execution block for testing ---
async def main_test():
    """Main function to test VAPI service calls when run directly."""
    logger.info("--- Starting VAPI Service Test ---")

    # --- Test sending a phone call ---
    # Use the global test variables
    global test_phone_number
    global test_last_name

    logger.info(f"Attempting to send call to: {test_phone_number}")

    # Prepare the params dictionary
    call_params = {
        'phone': test_phone_number,
        'name': test_last_name,
    }


    call_init_response = await send_phone_call_request(
        params=call_params
    )

    if not call_init_response or 'id' not in call_init_response:
        logger.error("Failed to initiate call or get call ID. Exiting test.")
        # Print the response received, even if it's an error from VAPI
        if call_init_response:
             print("VAPI Initiation Response:", json.dumps(call_init_response, indent=2))
        return

    call_id = call_init_response['id']
    logger.info(f"Call initiated successfully. Call ID: {call_id}")
    print("Initial Response:", json.dumps(call_init_response, indent=2))


    # --- Test checking call status ---
    logger.info(f"Starting status check loop for Call ID: {call_id}")
    max_checks = 10 # Limit the number of checks
    check_interval = 15 # Seconds between checks
    in_progress = True
    checks_done = 0

    while in_progress and checks_done < max_checks:
        checks_done += 1
        logger.info(f"Checking status... (Attempt {checks_done}/{max_checks})")
        await asyncio.sleep(check_interval) # Wait before checking

        call_status_response = await check_call_status(call_id)

        if call_status_response is None:
            logger.error("Error occurred while checking call status. Stopping checks.")
            in_progress = False # Stop loop on error
        elif call_status_response == {}: # Specific case for some API error formats, or could check 'error' key
             logger.warning(f"Call ID {call_id} status check returned empty or specific error indicator. Stopping checks.")
             print("Status Check Response:", json.dumps(call_status_response, indent=2))
             in_progress = False
        elif 'error' in call_status_response: # Check for error structure returned by exception handler
             logger.error(f"Call ID {call_id} status check returned an error: {call_status_response.get('detail', 'Unknown error')}. Stopping checks.")
             print("Status Check Response:", json.dumps(call_status_response, indent=2))
             in_progress = False
        else:
            # Successfully got status
            current_status = call_status_response.get('status', 'unknown')
            logger.info(f"Current call status: {current_status}")
            print("Full Status Response:", json.dumps(call_status_response, indent=2))

            # Check for terminal statuses (adjust based on VAPI documentation: ended, failed, canceled, error)
            # Note: VAPI documentation lists statuses like 'queued', 'ringing', 'in-progress', 'ended', 'failed'.
            terminal_statuses = ["ended", "failed", "canceled", "error"]
            if current_status in terminal_statuses:
                logger.info(f"Call reached terminal status: {current_status}. Stopping checks.")
                in_progress = False # Stop loop

    if checks_done >= max_checks and in_progress:
        logger.warning("Reached maximum status checks without reaching a terminal state.")

    logger.info("--- VAPI Service Test Finished ---")


if __name__ == "__main__":
    asyncio.run(main_test())
