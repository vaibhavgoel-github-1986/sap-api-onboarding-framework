"""
Base SAP Tool - Generic reusable pattern for all SAP API tools
"""

from abc import abstractmethod
from typing import Dict, Any
from langchain_core.tools import ToolException, BaseTool
from langchain_core.tools.base import ArgsSchema

from ..pydantic_models.sap_tech import (
    GenericAPIResponse,
    GenericAPIRequest,
    SAPServiceConfig,
)
from ..utils.logger import logger
from ..utils.sap_generic_service import sap_generic_service
from ..config import get_settings

# Get Config Settings
settings = get_settings()

class BaseSAPTool(BaseTool):
    """
    Base class for all SAP API tools. Provides common functionality and patterns.

    Each SAP tool should inherit from this class and implement:
    1. get_service_config() - Define the SAP service details
    2. Optionally override validate_request() for custom validation
    3. Optionally override process_response() for custom response handling
    """

    # Common configuration
    args_schema: ArgsSchema = GenericAPIRequest
    return_direct: bool = settings.tool_return_direct

    @abstractmethod
    def get_service_config(self, **kwargs) -> SAPServiceConfig:
        """
        Return the SAP service configuration for this tool.

        Args:
            **kwargs: Optional parameters that might influence service configuration

        Returns:
            SAPServiceConfig: Typed configuration object with service details

        Example:
            return SAPServiceConfig(
                service_name="ZSD_TABLE_SCHEMA",
                service_namespace="ZSB_TABLE_SCHEMA",
                entity_name="TableSchema",
                odata_version="v4",
                http_method="GET"
            )
        """
        pass

    def process_response(self, response: GenericAPIResponse, **kwargs) -> Any:
        """
        Process the API response. Override for custom response handling.

        Args:
            response: The API response
            **kwargs: Original request parameters

        Returns:
            Processed response (default: raw response data)

        Raises:
            ToolException: If response processing fails
        """
        if response.success and response.raw_response is not None:
            return response.raw_response
        else:
            raise ToolException(f"API call failed: {response.error_details}")

    def populate_request_params(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Populate request parameters from kwargs and service config.

        Args:
            **kwargs: Input parameters from the tool call

        Returns:
            Dict containing all parameters needed for SAP API call
        """
        return {
            "system_id": kwargs.get("system_id"),
            "http_method": kwargs.get("http_method"),
            "service_name": kwargs.get("service_name"),
            "service_namespace": kwargs.get("service_namespace"),
            "entity_name": kwargs.get("entity_name"),
            "odata_version": kwargs.get("odata_version"),
            "query_parameters": kwargs.get("query_parameters"),
            "request_body": kwargs.get("request_body"),
            "client_id": kwargs.get("client_id"),
            "username": kwargs.get("username"),
            "password": kwargs.get("password"),
        }

    def _run(self, **kwargs: Any) -> Any:
        """
        Execute the SAP API call with common error handling and logging.
        """
        try:

            # Get Parameters
            params = self.populate_request_params(**kwargs)

            # Validate request parameters
            if not params.get("system_id"):
                raise ToolException("Please provide the System you want to use (system_id is required)")

            http_method = params.get("http_method")

            # if http_method == "GET" and not params.get("query_parameters"):
            #     raise ToolException("Please provide query_parameters for a GET request")
            if http_method in ["POST", "PUT", "PATCH"] and not params.get(
                "request_body"
            ):
                raise ToolException(
                    "Please provide request_body for POST/PUT/PATCH requests"
                )

            # For Logging
            if http_method == "GET" and params.get("query_parameters"):
                logger.info(
                    f"Making a GET request with query parameters: {params.get('query_parameters')}"
                )
            elif http_method in ["POST", "PUT", "PATCH"]:
                logger.info(
                    f"Making a {http_method} request with body: {params.get('request_body')}"
                )
            else:
                logger.info(
                    f"Making a {http_method} request to SAP system: {params.get('system_id')}"
                )

            # Call the SAP API
            response: GenericAPIResponse = sap_generic_service.call_sap_api_generic(
                http_method=params.get("http_method"),
                service_name=params.get("service_name"),
                entity_name=params.get("entity_name"),
                service_namespace=params.get("service_namespace"),
                odata_version=params.get("odata_version"),
                query_parameters=params.get("query_parameters"),
                request_body=params.get("request_body"),
                system_id=params.get("system_id"),
                client_id=params.get("client_id"),
                username=params.get("username"),
                password=params.get("password"),
            )

            # Process and return response
            return self.process_response(response, **params)

        except Exception as e:
            logger.error(f"Error in {self.name}: {str(e)}")
            raise ToolException(f"{self.name} failed: {str(e)}") from e
