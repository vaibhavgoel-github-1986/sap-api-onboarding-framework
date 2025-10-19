import time
import requests
import base64
import traceback
from typing import Optional

from ..utils.logger import logger
from ..config import get_settings

# Config Settings
settings = get_settings()

# ✅ Global variables for token caching
_cached_azure_token = None
_azure_token_expiry = 0  # Stores Azure token expiry time (UNIX timestamp)


def get_azure_token() -> Optional[str]:
    """Get authentication token for Azure LLM."""
    global _cached_azure_token, _azure_token_expiry

    # Check if cached token is still valid
    if _cached_azure_token and time.time() < _azure_token_expiry:
        logger.info("Using cached token")
        return _cached_azure_token

    # Get Azure credentials from config
    client_id = settings.azure_client_id
    client_secret = settings.azure_client_secret
    token_url = settings.azure_token_url

    if not all([client_id, client_secret, token_url]):
        logger.error("Missing Azure credentials: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TOKEN_URL")
        return None

    # Type check passed, safe to call helper
    assert client_id and client_secret and token_url
    token = _fetch_token(client_id, client_secret, token_url, "Azure")
    if token:
        _cached_azure_token = token["access_token"]
        expires_in = token.get("expires_in", 3600)
        _azure_token_expiry = time.time() + expires_in - 600  # Refresh 10 mins before expiry        
        return _cached_azure_token
    
    return None


def _fetch_token(client_id: str, client_secret: str, token_url: str, service_name: str) -> Optional[dict]:
    """Helper function to fetch token from OAuth server."""
    logger.info(f"Fetching {service_name} oAuth Token")
    
    payload = "grant_type=client_credentials"
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}",
    }

    try:
        response = requests.post(token_url, headers=headers, data=payload)
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"{service_name} token fetched successfully")
        return response_data

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"{service_name} HTTP error: {http_err}")
    except Exception as err:
        logger.error(f"{service_name} error: {err}")
        traceback.print_exc()

    return None


def clear_auth_token():
    """
    Clears all cached authentication tokens.
    """
    global _cached_azure_token, _azure_token_expiry
    _cached_azure_token = None
    _azure_token_expiry = 0
