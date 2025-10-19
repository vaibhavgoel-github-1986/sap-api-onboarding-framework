"""
Configuration management for the SAP Tools application.
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables
load_dotenv()


class Settings:
    """Application settings with environment variable loading."""
    
    def __init__(self):
        # Server Configuration
        self.app_title = "SAP Tools API"
        self.app_version = "1.0.0"
        self.host = "0.0.0.0"
        self.port = 8000
        self.debug = False
        
        # Azure Authentication
        self.azure_app_key = os.getenv("AZURE_APP_KEY")
        self.azure_user_id = os.getenv("AZURE_USER_ID")
        self.azure_client_id = os.getenv("AZURE_CLIENT_ID")
        self.azure_client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.azure_token_url = os.getenv("AZURE_TOKEN_URL")
        
        # Azure OpenAI
        self.azure_endpoint = os.getenv("AZURE_ENDPOINT")
        self.azure_api_version = os.getenv("AZURE_API_VERSION")
        self.azure_deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME")
        
        # SAP Configuration
        self.sap_default_system_id = os.getenv("SAP_DEFAULT_SYSTEM_ID", "D2A")
        self.sap_username = os.getenv("SAP_USERNAME")
        self.sap_password = os.getenv("SAP_PASSWORD")
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Cache Configuration
        self.metadata_cache_ttl = int(os.getenv("METADATA_CACHE_TTL", "28800"))  # After 8 hours cache will reset
        
        # Security
        self.allowed_origins = ["http://localhost:3000"]
        
    def validate_required_settings(self) -> bool:
        """Validate that all required environment variables are set."""
        required_vars = [
            'azure_app_key', 'azure_user_id', 'azure_client_id', 
            'azure_client_secret', 'azure_token_url', 'azure_endpoint',
            'azure_api_version', 'azure_deployment_name', 'sap_username', 'sap_password'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(self, var):
                missing_vars.append(var.upper())
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        return True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.validate_required_settings()
    return settings


# SAP System configurations
SAP_SYSTEMS: Dict[str, Dict[str, Any]] = {
    "QHA": {
        "hostname": "https://saphec-qa.cisco.com:44300",
        "client_id": "300",
        "description": "QA System"
    },
    "Q2A": {
        "hostname": "https://saphec-qa2.cisco.com:44300", 
        "client_id": "300",
        "description": "QA2 System"
    },
    "RHA": {
        "hostname": "https://saphec-preprod.cisco.com:44300",
        "client_id": "300", 
        "description": "Pre-Production System"
    },
    "D2A": {
        "hostname": "https://saphec-dv2.cisco.com:44300",
        "client_id": "120",
        "description": "Development System"
    },
    "DHA": {
        "hostname": "https://saphec-dev.cisco.com:44300",
        "client_id": "120",
        "description": "Development System"
    },
    "SHA": {
        "hostname": "https://saphec-sb.cisco.com:44300",
        "client_id": "320",
        "description": "Sandbox System"
    }
}