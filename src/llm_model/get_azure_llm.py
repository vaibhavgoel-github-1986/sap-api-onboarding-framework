import os
import sys
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from typing import Optional
from datetime import datetime, timedelta
from pydantic import SecretStr

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from src.llm_model.get_auth_token import get_azure_token, clear_auth_token
    
# Load environment variables
load_dotenv()

# Global variables to track LLM instance and token expiration
_cached_llm_instance = None
_token_expiry_time = datetime.now()


def get_azure_llm(
    temperature: Optional[float] = None,
    deployment_name: Optional[str] = None,
    api_version: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
    app_key: Optional[str] = None,
    user_id: Optional[str] = None,
) -> AzureChatOpenAI:
    """
    Retrieves an instance of AzureChatOpenAI configured with the required parameters.
    Always creates a fresh instance with current token to avoid token expiry issues.

    Args:
        temperature (float): The randomness in output. Lower values are more deterministic.
        deployment_name (str): Azure deployment name. Defaults to config setting.
        api_version (str): Azure API version. Defaults to config setting.
        azure_endpoint (str): Azure API endpoint. Defaults to config setting.
        app_key (str): Application key. Defaults to config setting.
        user_id (str): User ID. Defaults to config setting.

    Returns:
        AzureChatOpenAI: The configured LLM instance.

    Raises:
        ValueError: If required parameters are missing or token retrieval fails.
    """

    # Use config defaults if parameters not provided
    azure_endpoint = azure_endpoint or os.getenv('AZURE_ENDPOINT')
    api_version = api_version or os.getenv('AZURE_API_VERSION')
    deployment_name = deployment_name or os.getenv('AZURE_DEPLOYMENT_NAME')
    temperature = temperature or 0.2

    app_key = app_key or os.getenv('AZURE_APP_KEY')
    user_id = user_id or os.getenv('AZURE_USER_ID')

    # ✅ Validate required parameters
    if not all([deployment_name, azure_endpoint, api_version, app_key, user_id]):
        raise ValueError(
            "Missing required parameters for the LLM. Please update the settings accordingly."
        )

    # ✅ Always get fresh authentication token to prevent expiry issues
    api_key = get_azure_token()
    if not api_key:
        raise ValueError("Failed to retrieve Cisco authentication token.")

    # ✅ Always create fresh LLM instance with current token
    # This prevents token expiry issues that cause TaskGroup errors
    llm_instance = AzureChatOpenAI(
        azure_deployment=deployment_name,
        azure_endpoint=azure_endpoint,
        api_key=SecretStr(api_key),
        api_version=api_version,
        verbose=True,
        temperature=temperature,
        model_kwargs={"user": f'{{"appkey": "{app_key}", "user": "{user_id}"}}'},
    )

    return llm_instance


def clear_llm_instance():
    """
    Clears the LLM instance and token expiry time.
    """
    global _cached_llm_instance, _token_expiry_time
    _cached_llm_instance = None
    clear_auth_token()
    _token_expiry_time = datetime.now()
