"""
Generic SAP API service for unified OData operations
"""

import os, sys
import time
from typing import Literal, Optional
from fastapi import HTTPException
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from src.utils.sap_api_client import (
    SAPApiClient,
    SAPServerException,
    SAPAuthorizationException,
)
from src.utils.sap_common import handle_sap_exceptions
from src.models.sap_tech import GenericAPIResponse
from src.utils.logger import logger

# Load environment variables
load_dotenv()

class SAPGenericService:
    """Service class for generic SAP API operations"""

    def __init__(self):
        """Initialize the SAP generic service"""
        pass

    @handle_sap_exceptions("making generic SAP API call")
    def call_sap_api_generic(
        self,
        http_method: str,
        service_name: str,
        entity_name: str,
        service_namespace: Optional[str] = None,
        odata_version: Literal["v2", "v4"] = "v4",
        query_parameters: Optional[dict] = None,
        request_body: Optional[dict] = None,
        system_id: Optional[str] = None,
        client_id: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> GenericAPIResponse:
        """
        Generic SAP API caller supporting all HTTP methods (GET, POST, PUT, PATCH, DELETE)

        This method provides a unified interface to call any SAP OData service with any HTTP method,
        making it suitable for:
        - GET: Reading data from entity sets
        - POST: Creating new entities
        - PUT/PATCH: Updating existing entities
        - DELETE: Removing entities
        - Custom function imports and actions

        Args:
            http_method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            service_name: SAP OData service name (required)
            entity_name: Entity name - can be entity set, entity key, function import, or custom path
            service_namespace: Service namespace (optional, defaults to service_name)
            odata_version: OData version - v2 or v4 (optional, defaults to v4)
            query_parameters: Dictionary of query parameters (e.g., $filter, $select, etc.)
            request_body: Request body data for POST/PUT/PATCH operations
            system_id: SAP system ID (optional)
            client_id: SAP client number (optional)
            username: SAP username (optional)
            password: SAP password (optional)

        Returns:
            GenericAPIResponse: Comprehensive response with request/response details
        """
        start_time = time.time()

        # Validate HTTP method
        valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
        http_method = http_method.upper()
        if http_method not in valid_methods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid HTTP method '{http_method}'. Supported: {', '.join(valid_methods)}",
            )

        if not system_id:
            raise HTTPException(status_code=400, detail="Please provide SAP system ID")

        if not service_name:
            raise HTTPException(status_code=400, detail="Service name is required")

        if not entity_name:
            raise HTTPException(status_code=400, detail="Entity name is required")

        # Validate odata_version
        if odata_version not in ["v2", "v4"]:
            raise HTTPException(
                status_code=400, detail="OData version must be 'v2' or 'v4'"
            )

        # Use service_name as namespace if not provided
        if not service_namespace:
            service_namespace = service_name

        # Initialize SAP API client
        client = SAPApiClient(
            client_id=client_id,
            system_id=system_id,
            username=username,
            password=password,
            service_name=service_name,
            service_namespace=service_namespace,
            odata_version=odata_version
        )

        logger.info(f"SAP API call: {http_method} {system_id}/{service_name}/{entity_name}")

        # Build complete URL
        service_path = client.get_service_path()
        base_url = client.build_service_url(service_path)
        # Clean up entity name - remove leading slash if present
        entity_name = entity_name.lstrip("/")
        full_url = f"{base_url}/{entity_name}"

        # Prepare query parameters
        if query_parameters is None:
            query_parameters = {}

        # Transform query parameters by adding $ prefix for OData standard parameters
        # This allows users to pass "filter" instead of "$filter", etc.
        odata_standard_params = {
            "filter",
            "select",
            "expand",
            "orderby",
            "top",
            "skip",
            "count",
            "search",
            "format",
            "inlinecount",
        }

        transformed_params = {}
        for key, value in query_parameters.items():
            # Add $ prefix if it's a standard OData parameter and doesn't already have it
            if key.lower() in odata_standard_params and not key.startswith("$"):
                transformed_params[f"${key}"] = value
            else:
                # Keep custom parameters as-is (e.g., sap-client, custom filters, etc.)
                transformed_params[key] = value

        # For POST requests, filter out OData system query options as SAP doesn't allow them
        # Only keep essential parameters like sap-client
        if http_method.upper() == "POST":
            allowed_post_params = {}
            for key, value in transformed_params.items():
                # Keep non-OData parameters (like sap-client) but exclude OData system query options
                # For POST requests, even $format might not be needed/allowed in some cases
                if not key.startswith("$"):
                    allowed_post_params[key] = value
                else:
                    logger.warning(f"Filtered OData parameter '{key}' for POST request")
            query_parameters = allowed_post_params
            logger.info(f"POST query parameters: {query_parameters}")
        else:
            query_parameters = transformed_params

        # Log the request details
        if query_parameters:
            logger.info(f"Query params: {query_parameters}")
        if request_body and http_method in ["POST", "PUT", "PATCH"]:
            logger.info(f"Request body: {request_body}")

        try:
            # Use the underlying _make_request_with_csrf method for automatic CSRF token handling
            response = client._make_request_with_csrf(
                method=http_method,
                url=full_url,
                params=query_parameters,
                data=request_body,
                headers=None,  # Let the client set appropriate headers
            )

            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"SAP API response status: {response.status_code} in {execution_time_ms} ms")

            # Capture the actual query parameters that were sent (including SAP client additions)
            final_query_params = query_parameters.copy()
            if "sap-client" not in final_query_params:
                final_query_params["sap-client"] = client.client_id
            if (
                odata_version == "v2"
                and "$format" not in final_query_params
                and "/$metadata" not in entity_name
            ):
                # Only add $format for non-POST requests in v2
                if http_method.upper() not in ["POST", "PUT", "PATCH", "DELETE"]:
                    final_query_params["$format"] = "json"

            # Convert all values to strings for the response model
            final_query_params_str = {k: str(v) for k, v in final_query_params.items()}

            # Parse response and extract data based on success
            success = 200 <= response.status_code < 300
            raw_response, record_count, error_details = self._parse_api_response(
                response, http_method, success, odata_version
            )

            # Build success message
            message = self._build_response_message(
                success, http_method, entity_name, record_count, error_details
            )

            # Filter out sensitive headers like set-cookie
            filtered_headers = {}
            if response.headers:
                for key, value in response.headers.items():
                    if key.lower() != "set-cookie":
                        filtered_headers[key] = value

            # Create user-friendly query parameters (remove $ prefix for standard OData params)
            user_friendly_params = self._create_user_friendly_params(
                final_query_params_str
            )

            return GenericAPIResponse(
                http_method=http_method,
                service_name=service_name,
                service_namespace=service_namespace,
                entity_name=entity_name,
                odata_version=odata_version,
                request_url=full_url,
                status_code=response.status_code,
                success=success,
                raw_response=raw_response,
                request_body=request_body,
                query_parameters=user_friendly_params,
                response_headers=filtered_headers,
                execution_time_ms=execution_time_ms,
                record_count=record_count,
                error_details=error_details,
                message=message,
            )

        except SAPServerException as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"SAP server error: {e}")
            return self._build_error_response(
                http_method,
                service_name,
                service_namespace,
                entity_name,
                odata_version,
                full_url,
                request_body,
                query_parameters,
                execution_time_ms,
                500,
                str(e),
            )
        except SAPAuthorizationException as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"SAP authorization error: {e}")
            return self._build_error_response(
                http_method,
                service_name,
                service_namespace,
                entity_name,
                odata_version,
                full_url,
                request_body,
                query_parameters,
                execution_time_ms,
                403,
                str(e),
            )
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"SAP API call failed: {str(e)}")
            return self._build_error_response(
                http_method,
                service_name,
                service_namespace,
                entity_name,
                odata_version,
                full_url,
                request_body,
                query_parameters,
                execution_time_ms,
                500,
                str(e),
            )

    def _create_user_friendly_params(self, query_params_dict):
        """
        Convert query parameters to user-friendly format by removing $ prefix from standard OData params
        """
        user_friendly = {}
        odata_standard_params = {
            "$filter": "filter",
            "$select": "select",
            "$expand": "expand",
            "$orderby": "orderby",
            "$top": "top",
            "$skip": "skip",
            "$count": "count",
            "$search": "search",
            "$format": "format",
            "$inlinecount": "inlinecount",
        }

        for key, value in query_params_dict.items():
            # Convert standard OData params to user-friendly names
            if key in odata_standard_params:
                user_friendly[odata_standard_params[key]] = value
            else:
                # Keep other params as-is
                user_friendly[key] = value

        return user_friendly

    def _parse_api_response(self, response, http_method, success, odata_version):
        """
        Parse API response and extract relevant data
        """
        raw_response = None
        record_count = None
        error_details = None

        try:
            if success:
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    raw_response = response.json()

                    # Extract record count for GET requests
                    if http_method == "GET":
                        data_array = self._extract_data_array(
                            raw_response, odata_version
                        )
                        record_count = len(data_array) if data_array else 0
                elif response.content:
                    # For non-JSON responses (like XML metadata)
                    raw_response = {
                        "content": (
                            response.text[:1000] + "..."
                            if len(response.text) > 1000
                            else response.text
                        )
                    }
                else:
                    # Empty response (common for DELETE, PUT operations)
                    raw_response = {
                        "status": "success",
                        "message": "Operation completed successfully",
                    }
            else:
                # Extract error details from failed response
                try:
                    if response.content:
                        content_type = response.headers.get("Content-Type", "")
                        if "application/json" in content_type:
                            error_data = response.json()
                            if "error" in error_data:
                                error_obj = error_data["error"]
                                if isinstance(error_obj, dict):
                                    error_details = error_obj.get("message", {})
                                    if isinstance(error_details, dict):
                                        error_details = error_details.get(
                                            "value", str(error_obj)
                                        )
                                    else:
                                        error_details = str(error_details)
                                else:
                                    error_details = str(error_obj)
                            else:
                                error_details = str(error_data)
                        else:
                            error_details = response.text[:500]
                    else:
                        error_details = f"HTTP {response.status_code}: No content"
                except Exception:
                    error_details = (
                        f"HTTP {response.status_code}: Unable to parse error response"
                    )

                raw_response = {
                    "error": error_details,
                    "status_code": response.status_code,
                }

        except Exception as e:
            logger.error(f"Error parsing API response: {e}")
            error_details = f"Response parsing error: {str(e)}"
            raw_response = {"error": error_details}

        return raw_response, record_count, error_details

    def _extract_data_array(self, raw_response, odata_version):
        """
        Extract data array from OData response (handles both V2 and V4 formats)
        """
        if not raw_response:
            return []

        try:
            if odata_version == "v2":
                # OData V2 format: data is in "d.results" or just "d" for single entities
                if "d" in raw_response:
                    d_content = raw_response["d"]
                    if "results" in d_content:
                        return d_content["results"]
                    elif isinstance(d_content, list):
                        return d_content
                    elif isinstance(d_content, dict):
                        return [d_content]  # Single entity
                return []
            else:
                # OData V4 format: data is in "value" array or root object for single entities
                if "value" in raw_response:
                    return raw_response["value"]
                elif isinstance(raw_response, list):
                    return raw_response
                elif isinstance(raw_response, dict) and "value" not in raw_response:
                    # Might be a single entity response
                    return [raw_response]
                return []

        except Exception as e:
            logger.error(f"Error extracting data array: {e}")
            return []

    def _build_response_message(
        self, success, http_method, entity_name, record_count, error_details
    ):
        """
        Build appropriate response message based on operation type and outcome
        """
        if success:
            if http_method == "GET":
                if record_count is not None:
                    return f"Successfully retrieved {record_count} record(s) from {entity_name}"
                else:
                    return f"Successfully retrieved data from {entity_name}"
            elif http_method == "POST":
                return f"Successfully created new entity in {entity_name}"
            elif http_method in ["PUT", "PATCH"]:
                return f"Successfully updated entity in {entity_name}"
            elif http_method == "DELETE":
                return f"Successfully deleted entity from {entity_name}"
            else:
                return f"Successfully executed {http_method} operation on {entity_name}"
        else:
            operation_verb = {
                "GET": "retrieve data from",
                "POST": "create entity in",
                "PUT": "update entity in",
                "PATCH": "update entity in",
                "DELETE": "delete entity from",
            }.get(http_method, f"execute {http_method} operation on")

            return f"Failed to {operation_verb} {entity_name}" + (
                f": {error_details}" if error_details else ""
            )

    def _build_error_response(
        self,
        http_method,
        service_name,
        service_namespace,
        entity_name,
        odata_version,
        request_url,
        request_body,
        query_parameters,
        execution_time_ms,
        status_code,
        error_message,
    ):
        """
        Build error response for failed API calls
        """
        user_friendly_params = self._create_user_friendly_params(query_parameters)

        return GenericAPIResponse(
            http_method=http_method,
            service_name=service_name,
            service_namespace=service_namespace,
            entity_name=entity_name,
            odata_version=odata_version,
            request_url=request_url,
            status_code=status_code,
            success=False,
            raw_response={"error": error_message},
            request_body=request_body,
            query_parameters=user_friendly_params,
            response_headers={},
            execution_time_ms=execution_time_ms,
            record_count=None,
            error_details=error_message,
            message=f"Generic SAP API call failed: {error_message}",
        )
