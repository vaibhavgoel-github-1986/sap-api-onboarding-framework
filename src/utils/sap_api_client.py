from http.client import HTTPException
import os
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

import json
from typing import Dict, List, Optional, Literal
from src.utils.logger import logger

# Load environment variables
load_dotenv()

SAP_SYSTEM_CONFIG = {
    "QHA": {
        "hostname": "https://saphec-qa.cisco.com:44300",
        "client_id": "300",
    },
    "Q2A": {
        "hostname": "https://saphec-qa2.cisco.com:44300",
        "client_id": "300",
    },
    "RHA": {
        "hostname": "https://saphec-preprod.cisco.com:44300",
        "client_id": "300",
    },
    "D2A": {
        "hostname": "https://saphec-dv2.cisco.com:44300",
        "client_id": "120",
    },
    "DHA": {
        "hostname": "https://saphec-dev.cisco.com:44300",
        "client_id": "120",
    },
    "SHA": {
        "hostname": "https://saphec-sb.cisco.com:44300",
        "client_id": "320",
    },
}


class SAPAPIException(Exception):
    """Custom exception for SAP API errors"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_detail: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_detail = error_detail
        super().__init__(self.message)


class SAPAuthenticationException(SAPAPIException):
    """Exception for SAP authentication errors (401)"""

    pass


class SAPAuthorizationException(SAPAPIException):
    """Exception for SAP authorization errors (403)"""

    pass


class SAPResourceNotFoundException(SAPAPIException):
    """Exception for SAP resource not found errors (404)"""

    pass


class SAPServerException(SAPAPIException):
    """Exception for SAP server errors (5xx)"""

    pass


class SAPApiClient:
    """Generic client for calling SAP OData APIs (both V2 and V4)"""

    def __init__(
        self,
        system_id: str,
        client_id: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        service_name: Optional[str] = None,
        service_namespace: Optional[str] = None,
        odata_version: Literal["v2", "v4"] = "v4",
        base_path: Optional[str] = None,
        timeout: int = 120,
    ):
        """
        Initialize the SAP API Client

        Args:
            client_id: SAP Client ID
            system_id: System identifier (default: "DHA")
            username: SAP username
            password: SAP password
            service_name: For OData V4 only - the service name to use when building the service path
            service_namespace: For OData V4 only - the service namespace (if different from service_name)
            odata_version: OData version ("v2" or "v4")
            base_path: Base path for SAP OData services (if None, will be set based on version)
            timeout: Request timeout in seconds
        """

        # Use provided system config or default
        self.system_id = system_id.upper()
        self.client_id = client_id or SAP_SYSTEM_CONFIG[self.system_id]["client_id"]
        self.username = username or os.getenv("SAP_USER_ID") or os.getenv("SAP_USERNAME")
        self.password = password or os.getenv("SAP_PASSWORD")
        
        self.timeout = timeout
        self.odata_version = odata_version
        self.service_name = service_name
        self.service_namespace = service_namespace 

        if self.system_id not in SAP_SYSTEM_CONFIG:
            raise ValueError(f"System ID '{self.system_id}' not found in configuration")
            
        if not self.username or not self.password:
            raise ValueError("Please provide SAP Credentials")

        self.hostname = SAP_SYSTEM_CONFIG[self.system_id]["hostname"]

        # Set base path according to OData version if not provided
        if base_path is None:
            self.base_path = (
                "/sap/opu/odata4/sap" if odata_version == "v4" else "/sap/opu/odata/sap"
            )
        else:
            self.base_path = base_path

        logger.info(f"SAP API Client initialized: {self.hostname} ({odata_version}) Client: {self.client_id}")
        if service_name:
            logger.debug(f"Service: {service_name}")
            if odata_version == "v4":
                service_path = self.get_service_path()
                logger.debug(f"Service path: {service_path}")

    def build_entity_key(self, **key_values) -> str:
        """
        Build entity key string from key-value pairs

        Args:
            **key_values: Key-value pairs for the entity key

        Returns:
            Formatted entity key string

        Examples:
            build_entity_key(id=123) -> "(123)"
            build_entity_key(subscriptionrefid='SR100062', weborderid='96695165')
                -> "(subscriptionrefid='SR100062',weborderid='96695165')"
        """
        if not key_values:
            return ""

        if len(key_values) == 1:
            # Single key
            key, value = next(iter(key_values.items()))
            if isinstance(value, str):
                return f"('{value}')"
            else:
                return f"({value})"
        else:
            # Composite key
            key_parts = []
            for key, value in key_values.items():
                if isinstance(value, str):
                    key_parts.append(f"{key}='{value}'")
                else:
                    key_parts.append(f"{key}={value}")
            return f"({','.join(key_parts)})"

    def build_advanced_filter(self, field_name: str, value: str) -> str:
        """
        Build OData filter expression with advanced operator support

        Args:
            field_name: The OData field name to filter on
            value: The filter value (may contain operators, wildcards, or comma-separated values)

        Returns:
            str: OData filter expression

        Examples:
            build_advanced_filter("ConfigValue", "ne:NA") -> "ConfigValue ne 'NA'"
            build_advanced_filter("ConfigValue", "ne: NA ") -> "ConfigValue ne 'NA'"
            build_advanced_filter("ConfigValue", "eq:test") -> "ConfigValue eq 'test'"
            build_advanced_filter("SubsRefID", "SR*") -> "startswith(SubsRefID, 'SR')"
            build_advanced_filter("SubsRefID", "SR1155405") -> "SubsRefID eq 'SR1155405'"
            build_advanced_filter("ConfigKey", "CIS_CC_USAGE_TYPE,CIS_CC_ASSET_TYPE") -> "(ConfigKey eq 'CIS_CC_USAGE_TYPE' or ConfigKey eq 'CIS_CC_ASSET_TYPE')"
        """
        # Trim the input value first
        value = value.strip()

        # Check for comma-separated values (multiple values)
        if "," in value and ":" not in value:
            # Split by comma and build OR conditions for multiple values
            values = [v.strip() for v in value.split(",") if v.strip()]
            if len(values) > 1:
                or_conditions = []
                for val in values:
                    # Process each value individually (may contain wildcards)
                    individual_filter = self.build_filter_with_wildcards(
                        field_name, val
                    )
                    or_conditions.append(individual_filter)
                return f"({' or '.join(or_conditions)})"
            else:
                # Single value after splitting, process normally
                value = values[0] if values else value

        # Check for operator syntax (operator:value)
        if ":" in value and len(value.split(":", 1)) == 2:
            operator, filter_value = value.split(":", 1)
            operator = operator.lower().strip()  # Trim operator
            filter_value = filter_value.strip()  # Trim filter value

            if operator == "ne":
                return f"{field_name} ne '{filter_value}'"
            elif operator == "eq":
                return f"{field_name} eq '{filter_value}'"
            elif operator == "gt":
                return f"{field_name} gt '{filter_value}'"
            elif operator == "ge":
                return f"{field_name} ge '{filter_value}'"
            elif operator == "lt":
                return f"{field_name} lt '{filter_value}'"
            elif operator == "le":
                return f"{field_name} le '{filter_value}'"
            elif operator == "contains":
                return f"contains({field_name}, '{filter_value}')"
            elif operator == "startswith":
                return f"startswith({field_name}, '{filter_value}')"
            elif operator == "endswith":
                return f"endswith({field_name}, '{filter_value}')"
            else:
                # Unknown operator, treat as exact match with original value
                return f"{field_name} eq '{value}'"
        else:
            # Fall back to wildcard processing
            return self.build_filter_with_wildcards(field_name, value)

    def build_filter_with_wildcards(self, field_name: str, value: str) -> str:
        """
        Build OData filter expression with wildcard pattern support

        Args:
            field_name: The OData field name to filter on
            value: The filter value (may contain wildcards *)

        Returns:
            str: OData filter expression

        Examples:
            build_filter_with_wildcards("SubsRefID", "SR*") -> "startswith(SubsRefID, 'SR')"
            build_filter_with_wildcards("SubsRefID", "*1155405") -> "endswith(SubsRefID, '1155405')"
            build_filter_with_wildcards("SubsRefID", "SR*405") -> "contains(SubsRefID, 'SR405')"
            build_filter_with_wildcards("SubsRefID", "SR1155405") -> "SubsRefID eq 'SR1155405'"
        """
        if "*" in value:
            if value.endswith("*"):
                # Pattern like "SR*" or "LNP_TST*"
                prefix = value[:-1]
                return f"startswith({field_name}, '{prefix}')"
            elif value.startswith("*"):
                # Pattern like "*SR1155405"
                suffix = value[1:]
                return f"endswith({field_name}, '{suffix}')"
            else:
                # Pattern like "SR*405" - use contains for middle wildcards
                pattern = value.replace("*", "")
                return f"contains({field_name}, '{pattern}')"
        else:
            # Exact match
            return f"{field_name} eq '{value}'"

    def build_date_range_filter(
        self,
        field_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """
        Build OData filter expression for date range filtering

        Args:
            field_name: The OData datetime field name to filter on
            start_date: Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
            end_date: End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)

        Returns:
            str: OData filter expression for date range

        Examples:
            build_date_range_filter("CreatedAt", "2024-01-01", "2024-12-31")
                -> "CreatedAt ge 2024-01-01T00:00:00Z and CreatedAt le 2024-12-31T23:59:59Z"
            build_date_range_filter("ChangedAt", "2024-06-01")
                -> "ChangedAt ge 2024-06-01T00:00:00Z"
            build_date_range_filter("CreatedAt", end_date="2024-06-30")
                -> "CreatedAt le 2024-06-30T23:59:59Z"
        """
        from datetime import datetime

        filters = []

        if start_date:
            # If only date is provided (YYYY-MM-DD), add time to start of day
            if len(start_date) == 10:  # YYYY-MM-DD format
                start_datetime = f"{start_date}T00:00:00Z"
            else:
                # Assume full datetime is provided, ensure Z suffix for UTC
                start_datetime = (
                    start_date if start_date.endswith("Z") else f"{start_date}Z"
                )
            filters.append(f"{field_name} ge {start_datetime}")

        if end_date:
            # If only date is provided (YYYY-MM-DD), add time to end of day
            if len(end_date) == 10:  # YYYY-MM-DD format
                end_datetime = f"{end_date}T23:59:59Z"
            else:
                # Assume full datetime is provided, ensure Z suffix for UTC
                end_datetime = end_date if end_date.endswith("Z") else f"{end_date}Z"
            filters.append(f"{field_name} le {end_datetime}")

        return " and ".join(filters)

    def _extract_error_message_v4(self, error_obj: dict) -> str:
        """
        Extract error message from OData v4 error format

        Args:
            error_obj: The error object from v4 response

        Returns:
            Formatted error message string
        """
        # Extract the main error message
        if isinstance(error_obj.get("message"), str):
            error_msg = error_obj["message"]
        elif isinstance(error_obj.get("message"), dict):
            error_msg = error_obj["message"].get("value", "Unknown SAP error")
        else:
            error_msg = str(error_obj)

        # Extract error code if available
        error_code = error_obj.get("code", "")

        # Extract additional details from innererror if available (v4 specific)
        additional_info = ""
        if "innererror" in error_obj:
            inner_error = error_obj["innererror"]
            if "ErrorDetails" in inner_error:
                error_details = inner_error["ErrorDetails"]
                # Extract service information
                if "@SAP__common.Application" in error_details:
                    app_info = error_details["@SAP__common.Application"]
                    service_id = app_info.get("ServiceId", "")
                    service_version = app_info.get("ServiceVersion", "")
                    if service_id:
                        additional_info = f" (Service: {service_id}"
                        if service_version:
                            additional_info += f" v{service_version}"
                        additional_info += ")"

                # Extract resolution info
                if "@SAP__common.ErrorResolution" in error_details:
                    resolution = error_details["@SAP__common.ErrorResolution"]
                    analysis = resolution.get("Analysis", "")
                    if analysis:
                        additional_info += f" Analysis: {analysis}"

        # Build complete error message
        if error_code:
            return f"[{error_code}] {error_msg}{additional_info}"
        else:
            return f"{error_msg}{additional_info}"

    def _extract_error_message_v2(self, error_obj: dict) -> str:
        """
        Extract error message from OData v2 error format

        Args:
            error_obj: The error object from v2 response

        Returns:
            Formatted error message string
        """
        error_msg = "Unknown SAP error"
        error_code = ""

        # v2 can have different error structures
        if isinstance(error_obj.get("message"), str):
            error_msg = error_obj["message"]
        elif isinstance(error_obj.get("message"), dict):
            # v2 sometimes has message as object with lang and value
            message_obj = error_obj["message"]
            if "value" in message_obj:
                error_msg = message_obj["value"]
            elif "text" in message_obj:
                error_msg = message_obj["text"]
            else:
                error_msg = str(message_obj)
        elif "error_description" in error_obj:
            error_msg = error_obj["error_description"]
        elif "description" in error_obj:
            error_msg = error_obj["description"]
        elif isinstance(error_obj, str):
            error_msg = error_obj
        else:
            # Try to get any meaningful text from the error object
            if isinstance(error_obj, dict):
                for key in ["text", "details", "reason"]:
                    if key in error_obj:
                        error_msg = str(error_obj[key])
                        break
                else:
                    error_msg = str(error_obj)

        # Extract error code (v2 format)
        if "code" in error_obj:
            error_code = error_obj["code"]
        elif "error_code" in error_obj:
            error_code = error_obj["error_code"]

        # v2 might have additional details in different structure
        additional_info = ""
        if "innererror" in error_obj:
            inner_error = error_obj["innererror"]
            if isinstance(inner_error, dict):
                # v2 innererror structure can be different
                if "errordetails" in inner_error:
                    details = inner_error["errordetails"]
                    if isinstance(details, list) and details:
                        # Sometimes v2 has error details as array
                        first_detail = details[0]
                        if isinstance(first_detail, dict) and "message" in first_detail:
                            additional_info = f" Detail: {first_detail['message']}"
                elif "message" in inner_error:
                    additional_info = f" Detail: {inner_error['message']}"

        # Build complete error message
        if error_code:
            return f"[{error_code}] {error_msg}{additional_info}"
        else:
            return f"{error_msg}{additional_info}"

    def _get_auth(self):
        """Return HTTP Basic Auth object"""
        if self.username is None or self.password is None:
            raise ValueError("Username and password must be provided for authentication")
        return HTTPBasicAuth(self.username, self.password)

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> requests.Response:
        """Make HTTP request to SAP API with improved error handling"""
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if headers:
            default_headers.update(headers)

        # Ensure sap-client is included in params if not already in URL
        if params is None:
            params = {}

        if "sap-client" not in params and "sap-client=" not in url:
            params["sap-client"] = self.client_id

        # For V2, ensure $format=json is included if not already in URL
        # Skip this for metadata URLs and for state-changing operations that might not allow SystemQueryOptions
        if (
            self.odata_version == "v2"
            and "$format" not in params
            and "$format=" not in url
            and "/$metadata" not in url
            and method.upper() not in ["POST", "PUT", "PATCH", "DELETE"]
        ):
            params["$format"] = "json"

        try:
            logger.debug(f"Making {method} request to {url}")
            logger.debug(f"Params: {params}")

            response = requests.request(
                method=method,
                url=url,
                auth=self._get_auth(),
                params=params,
                json=data,
                headers=default_headers,
                timeout=self.timeout,
            )

            # Check for common SAP error patterns in successful responses
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    try:
                        response_data = response.json()

                        # Check for direct error object in response (v4 format)
                        if response_data and "error" in response_data:
                            error_obj = response_data["error"]
                            error_msg = self._extract_error_message_v4(error_obj)

                            logger.error(
                                f"SAP API error in 200 response (v4 format): {error_msg}"
                            )

                            # Map error codes to appropriate exception types
                            if any(
                                pattern in error_msg.lower()
                                for pattern in ["404", "not found", "not published"]
                            ):
                                raise SAPResourceNotFoundException(
                                    f"SAP API error: {error_msg}"
                                )
                            elif any(
                                pattern in error_msg.lower()
                                for pattern in ["403", "forbidden", "access denied"]
                            ):
                                raise SAPAuthorizationException(
                                    f"SAP API error: {error_msg}"
                                )
                            elif any(
                                pattern in error_msg.lower()
                                for pattern in ["401", "unauthorized"]
                            ):
                                raise SAPAuthenticationException(
                                    f"SAP API error: {error_msg}"
                                )
                            else:
                                raise SAPAPIException(f"SAP API error: {error_msg}")

                        # Check for OData v2 specific error patterns in 'd' wrapper
                        elif (
                            response_data
                            and "d" in response_data
                            and isinstance(response_data["d"], dict)
                        ):
                            d_data = response_data["d"]
                            if "error" in d_data:
                                error_obj = d_data["error"]
                                error_msg = self._extract_error_message_v2(error_obj)

                                logger.error(
                                    f"SAP API error in 200 response (v2 format): {error_msg}"
                                )

                                # Map error codes to appropriate exception types
                                if any(
                                    pattern in error_msg.lower()
                                    for pattern in ["404", "not found", "not published"]
                                ):
                                    raise SAPResourceNotFoundException(
                                        f"SAP API error: {error_msg}"
                                    )
                                elif any(
                                    pattern in error_msg.lower()
                                    for pattern in ["403", "forbidden", "access denied"]
                                ):
                                    raise SAPAuthorizationException(
                                        f"SAP API error: {error_msg}"
                                    )
                                elif any(
                                    pattern in error_msg.lower()
                                    for pattern in ["401", "unauthorized"]
                                ):
                                    raise SAPAuthenticationException(
                                        f"SAP API error: {error_msg}"
                                    )
                                else:
                                    raise SAPAPIException(f"SAP API error: {error_msg}")

                            # Check for empty results that might indicate an error
                            elif "results" in d_data and len(d_data["results"]) == 0:
                                # For count operations, 0 results might be legitimate
                                if "/$count" not in url and "__count" not in d_data:
                                    logger.warning(
                                        f"Empty results returned from SAP API: {url}"
                                    )

                        # Check for OData v4 empty value array that might indicate service not found
                        elif (
                            "value" in response_data
                            and len(response_data["value"]) == 0
                        ):
                            # For count operations, 0 results might be legitimate
                            if "/$count" not in url:
                                logger.warning(
                                    f"Empty results returned from SAP API: {url}"
                                )

                    except json.JSONDecodeError:
                        # If response is not JSON, check if it contains error text
                        response_text = response.text.lower()
                        if any(
                            error_keyword in response_text
                            for error_keyword in [
                                "error",
                                "exception",
                                "not found",
                                "service unavailable",
                                "internal server error",
                            ]
                        ):
                            logger.error(
                                f"SAP API returned non-JSON error response: {response.text[:500]}"
                            )
                            raise SAPAPIException(
                                f"SAP API error: {response.text[:500]}"
                            )

                # Check for XML error responses (sometimes SAP returns XML errors)
                elif "application/xml" in content_type or "text/xml" in content_type:
                    response_text = response.text.lower()
                    if any(
                        error_keyword in response_text
                        for error_keyword in [
                            "error",
                            "exception",
                            "not found",
                            "service unavailable",
                        ]
                    ):
                        logger.error(
                            f"SAP API returned XML error response: {response.text[:500]}"
                        )
                        raise SAPAPIException(f"SAP API error: {response.text[:500]}")

                # Check for HTML error pages (SAP sometimes returns HTML error pages)
                elif "text/html" in content_type:
                    response_text = response.text.lower()
                    if any(
                        error_keyword in response_text
                        for error_keyword in [
                            "error",
                            "exception",
                            "not found",
                            "service unavailable",
                            "internal server error",
                        ]
                    ):
                        logger.error(
                            f"SAP API returned HTML error page: {response.text[:500]}"
                        )
                        raise SAPAPIException(
                            f"SAP API returned HTML error page - service may not be available"
                        )

            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_detail = ""

            # Try to extract detailed error messages for both OData v2 and v4
            try:
                if "application/json" in e.response.headers.get("Content-Type", ""):
                    data = e.response.json()

                    # Handle OData v4 format: direct error object
                    if data and "error" in data:
                        error_obj = data["error"]
                        error_detail = self._extract_error_message_v4(error_obj)

                    # Handle OData v2 format: error wrapped in 'd' object
                    elif (
                        data
                        and "d" in data
                        and isinstance(data["d"], dict)
                        and "error" in data["d"]
                    ):
                        error_obj = data["d"]["error"]
                        error_detail = self._extract_error_message_v2(error_obj)

                    # Handle other v2 error patterns (sometimes error is at root level in v2)
                    elif (
                        self.odata_version == "v2"
                        and data
                        and any(
                            key in data
                            for key in ["error_description", "error", "message"]
                        )
                    ):
                        error_detail = self._extract_error_message_v2(data)

                    else:
                        # Fallback: try to extract any meaningful error info
                        error_detail = str(data)[:500]

            except Exception as parse_error:
                logger.debug(f"Failed to parse error response: {parse_error}")
                # Fallback to raw response text
                error_detail = e.response.text[:500] if e.response.text else ""

            # Map common SAP error codes to specific exceptions
            if status_code == 401:
                error_msg = (
                    f"Authentication failed: {error_detail or 'Invalid credentials'}"
                )
                logger.error(error_msg)
                raise SAPAuthenticationException(error_msg, status_code, error_detail)
            elif status_code == 403:
                error_msg = f"Authorization failed: {error_detail or 'Insufficient permissions'}"
                logger.error(error_msg)
                raise SAPAuthorizationException(error_msg, status_code, error_detail)
            elif status_code == 404:
                error_msg = f"Resource not found: {error_detail or 'Invalid service path or entity set'}"
                logger.error(error_msg)
                raise SAPResourceNotFoundException(error_msg, status_code, error_detail)
            elif status_code >= 500:
                error_msg = (
                    f"SAP server error: {error_detail or 'Internal server error'}"
                )
                logger.error(error_msg)
                raise SAPServerException(error_msg, status_code, error_detail)
            else:
                error_msg = f"HTTP error {status_code}: {error_detail or str(e)}"
                logger.error(error_msg)
                raise SAPAPIException(error_msg, status_code, error_detail)

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            raise SAPAPIException(error_msg)
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            raise SAPAPIException(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(error_msg)
            raise SAPAPIException(error_msg)

    def _get_csrf_token(self, service_url: str) -> tuple[str, dict]:
        """
        Get CSRF token from SAP system for state-changing operations (POST, PUT, PATCH, DELETE)

        Args:
            service_url: The service URL to get the token from

        Returns:
            tuple: (csrf_token, cookies) - The CSRF token and session cookies
        """
        try:
            # Make a GET request to fetch CSRF token
            csrf_headers = {"X-CSRF-Token": "Fetch", "Accept": "application/json"}

            # For metadata requests, also add XML accept header
            if "/$metadata" in service_url:
                csrf_headers["Accept"] = "application/xml, application/json"

            # Add sap-client parameter
            csrf_params = {"sap-client": self.client_id}

            # For v2 services, add format parameter
            if self.odata_version == "v2" and "/$metadata" not in service_url:
                csrf_params["$format"] = "json"

            logger.debug(f"Fetching CSRF token from {service_url}")
            logger.debug(f"CSRF headers: {csrf_headers}")
            logger.debug(f"CSRF params: {csrf_params}")

            response = requests.get(
                url=service_url,
                auth=self._get_auth(),
                headers=csrf_headers,
                params=csrf_params,
                timeout=self.timeout,
            )

            logger.debug(f"CSRF token response: {response.status_code}")

            # Check if we got a permission error during CSRF fetch
            if response.status_code == 403:
                logger.error(f"Access denied for CSRF token from {service_url}")
                error_detail = "CSRF token fetch failed - insufficient permissions"

                # Try to get more detailed error from response
                try:
                    if response.content and "application/json" in response.headers.get(
                        "Content-Type", ""
                    ):
                        error_data = response.json()
                        if "error" in error_data:
                            error_obj = error_data["error"]
                            if isinstance(error_obj, dict):
                                error_detail = error_obj.get("message", {})
                                if isinstance(error_detail, dict):
                                    error_detail = error_detail.get(
                                        "value",
                                        "CSRF token fetch failed - insufficient permissions",
                                    )
                                else:
                                    error_detail = (
                                        str(error_detail)
                                        if error_detail
                                        else "CSRF token fetch failed - insufficient permissions"
                                    )
                except:
                    pass  # Use default error detail

                raise SAPAuthorizationException(
                    f"Access denied when fetching CSRF token. Check user permissions for service.",
                    403,
                    str(error_detail),
                )

            response.raise_for_status()

            # Extract CSRF token from response headers
            csrf_token = response.headers.get("X-CSRF-Token")
            if not csrf_token:
                available_headers = list(response.headers.keys())
                logger.error(
                    f"CSRF token not found in response headers. Available headers: {available_headers}"
                )
                raise SAPAPIException(
                    f"CSRF token not found in response headers. Available headers: {available_headers}"
                )

            # Extract session cookies for subsequent requests
            session_cookies = response.cookies.get_dict()

            logger.debug(f"CSRF token retrieved: {csrf_token[:10]}... ({len(session_cookies)} cookies)")
            return csrf_token, session_cookies

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error when fetching CSRF token: {e.response.status_code}"
            if e.response.content:
                try:
                    error_data = e.response.json()
                    if "error" in error_data:
                        error_detail = error_data["error"].get("message", {})
                        if isinstance(error_detail, dict):
                            error_detail = error_detail.get(
                                "value", str(error_data["error"])
                            )
                        error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {e.response.text[:200]}"
            logger.error(error_msg)
            raise SAPAPIException(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get CSRF token: {str(e)}"
            logger.error(error_msg)
            raise SAPAPIException(error_msg)

    def _make_request_with_csrf(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> requests.Response:
        """
        Make HTTP request with automatic CSRF token handling for state-changing operations

        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            data: Request body data
            headers: Additional headers

        Returns:
            requests.Response: The HTTP response
        """
        # For GET, HEAD, OPTIONS requests, use regular _make_request (no CSRF needed)
        if method.upper() in ["GET", "HEAD", "OPTIONS"]:
            return self._make_request(method, url, params, data, headers)

        # For state-changing operations, get CSRF token first
        try:
            # Use the base service URL to get CSRF token
            service_path = self.get_service_path()
            service_url = self.build_service_url(service_path)

            logger.debug(f"Getting CSRF token for {method} request")

            # Try to get CSRF token from metadata endpoint first (recommended approach)
            metadata_url = f"{service_url}/$metadata"
            try:
                logger.debug("Trying CSRF token from metadata endpoint")
                csrf_token, session_cookies = self._get_csrf_token(metadata_url)
                logger.debug("CSRF token retrieved from metadata")
            except (SAPAPIException, SAPAuthorizationException) as metadata_error:
                logger.debug(f"Metadata CSRF failed: {metadata_error}")
                # Fallback: try to get CSRF token from service root
                logger.debug("Trying CSRF token from service root")
                try:
                    csrf_token, session_cookies = self._get_csrf_token(service_url)
                    logger.debug("CSRF token retrieved from service root")
                except Exception as service_error:
                    logger.error(f"Service root CSRF failed: {service_error}")

                    # If the original error was authorization-related, re-raise it with context
                    if isinstance(metadata_error, SAPAuthorizationException):
                        raise SAPAuthorizationException(
                            f"Access denied for service {self.service_name}. User might not have permissions for this service or CSRF token operations.",
                            403,
                            f"CSRF token fetch failed for both metadata and service root endpoints. Original metadata error: {metadata_error.error_detail}",
                        )
                    else:
                        raise SAPAPIException(
                            f"Could not obtain CSRF token from metadata or service root endpoints. Metadata error: {metadata_error}, Service root error: {service_error}"
                        )

            # Prepare headers with CSRF token
            csrf_headers = {
                "X-CSRF-Token": csrf_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            if headers:
                csrf_headers.update(headers)

            # Ensure sap-client is included in params
            if params is None:
                params = {}
            if "sap-client" not in params and "sap-client=" not in url:
                params["sap-client"] = self.client_id

            # For V2, ensure $format=json for non-metadata URLs, but exclude for POST requests
            # as SAP may not allow SystemQueryOptions for POST operations
            if (
                self.odata_version == "v2"
                and "$format" not in params
                and "$format=" not in url
                and "/$metadata" not in url
                and method.upper() not in ["POST", "PUT", "PATCH", "DELETE"]
            ):
                params["$format"] = "json"

            logger.debug(f"Making {method} request with CSRF token")

            # Make the actual request with CSRF token and session cookies
            response = requests.request(
                method=method,
                url=url,
                auth=self._get_auth(),
                params=params,
                json=data,
                headers=csrf_headers,
                cookies=session_cookies,
                timeout=self.timeout,
            )

            logger.debug(f"Request response: {response.status_code}")

            # Handle SAP-specific error patterns (same as _make_request)
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    try:
                        response_data = response.json()
                        if "error" in response_data:
                            error_obj = response_data["error"]

                            if isinstance(error_obj.get("message"), str):
                                error_msg = error_obj["message"]
                            elif isinstance(error_obj.get("message"), dict):
                                error_msg = error_obj["message"].get(
                                    "value", "Unknown SAP error"
                                )
                            else:
                                error_msg = "Unknown SAP error"

                            error_code = error_obj.get("code", "")
                            if error_code:
                                error_msg = f"[{error_code}] {error_msg}"

                            logger.error(f"SAP API error: {error_msg}")
                            raise SAPAPIException(f"SAP API error: {error_msg}")
                    except json.JSONDecodeError:
                        pass

            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_detail = ""

            # Try to extract detailed error messages
            try:
                if "application/json" in e.response.headers.get("Content-Type", ""):
                    data = e.response.json()
                    if data and "error" in data:
                        error_obj = data["error"]
                        if isinstance(error_obj.get("message"), str):
                            error_detail = error_obj["message"]
                        elif isinstance(error_obj.get("message"), dict):
                            error_detail = error_obj["message"].get("value", "")

                        error_code = error_obj.get("code", "")
                        if error_code:
                            error_detail = f"[{error_code}] {error_detail}"
            except (json.JSONDecodeError, KeyError, TypeError):
                error_detail = e.response.text[:500] if e.response.text else ""

            # Handle specific HTTP status codes
            if status_code == 401:
                error_msg = (
                    f"Authentication failed: {error_detail or 'Invalid credentials'}"
                )
                logger.error(error_msg)
                raise SAPAuthenticationException(error_msg, status_code, error_detail)
            elif status_code == 403:
                error_msg = (
                    f"Access denied: {error_detail or 'Insufficient permissions'}"
                )
                logger.error(error_msg)
                raise SAPAuthorizationException(error_msg, status_code, error_detail)
            elif status_code == 404:
                error_msg = f"Resource not found: {error_detail or 'Invalid service path or entity set'}"
                logger.error(error_msg)
                raise SAPResourceNotFoundException(error_msg, status_code, error_detail)
            elif status_code >= 500:
                error_msg = (
                    f"SAP server error: {error_detail or 'Internal server error'}"
                )
                logger.error(error_msg)
                raise SAPServerException(error_msg, status_code, error_detail)
            else:
                error_msg = f"HTTP error {status_code}: {error_detail or str(e)}"
                logger.error(error_msg)
                raise SAPAPIException(error_msg, status_code, error_detail)

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            raise SAPAPIException(error_msg)
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            raise SAPAPIException(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(error_msg)
            raise SAPAPIException(error_msg)

    def build_service_url(self, service_path: str) -> str:
        """
        Build complete service URL based on OData version

        Args:
            service_path: The specific OData service path

        Returns:
            Complete URL to the OData service
        """
        # Just return the base URL without query parameters
        # Parameters will be added in get_data method
        return f"{self.hostname}{self.base_path}/{service_path}"

    def get_metadata(self, service_path: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Fetch metadata from an OData service (V2 or V4)

        Args:
            service_path: The specific OData service path or service name (optional if service_name was provided at initialization)

        Returns:
            Dictionary of entity types and their properties
        """
        # If no service_path is provided, try to use service_name
        if not service_path and self.service_name:
            service_path = self.get_service_path()
        elif service_path and self.odata_version == "v4" and "/" not in service_path:
            # If service_path looks like a service_name for V4, convert it
            service_path = self.get_service_path(service_path)

        if not service_path:
            raise ValueError("No service path or service name provided")

        url = f"{self.build_service_url(service_path)}/$metadata"

        # Define parameters with sap-client explicitly included
        params = {"sap-client": self.client_id}

        try:
            response = self._make_request(
                "GET", url, params=params, headers={"Accept": "application/xml"}
            )
            root = ET.fromstring(response.text)

            entities = {}

            if self.odata_version == "v4":
                # OData V4 namespace and structure
                namespace = {"edm": "http://docs.oasis-open.org/odata/ns/edm"}
                entity_types = root.findall(".//edm:EntityType", namespace)

                for entity in entity_types:
                    entity_name = entity.attrib.get("Name")
                    if entity_name:
                        properties = [
                            prop.attrib["Name"]
                            for prop in entity.findall("edm:Property", namespace)
                        ]
                        entities[entity_name] = properties
            else:
                # OData V2 namespace and structure
                namespace = {
                    "edmx": "http://schemas.microsoft.com/ado/2007/06/edmx",
                    "edm": "http://schemas.microsoft.com/ado/2008/09/edm",
                }

                # In V2, entity types are inside Schema elements
                schema_elements = root.findall(".//edm:Schema", namespace)
                for schema in schema_elements:
                    entity_types = schema.findall("edm:EntityType", namespace)
                    for entity in entity_types:
                        entity_name = entity.attrib.get("Name")
                        if entity_name:
                            properties = [
                                prop.attrib["Name"]
                                for prop in entity.findall("edm:Property", namespace)
                            ]
                            entities[entity_name] = properties

            return entities

        except Exception as e:
            logger.error(f"Error fetching metadata: {e}")
            return {}

    def get_raw_metadata(self, service_path: Optional[str] = None) -> str:
        """
        Fetch raw metadata XML from an OData service (V2 or V4)

        Args:
            service_path: The specific OData service path or service name (optional if service_name was provided at initialization)

        Returns:
            Raw metadata XML as string
        """
        # If no service_path is provided, try to use service_name
        if not service_path and self.service_name:
            service_path = self.get_service_path()
        elif service_path and self.odata_version == "v4" and "/" not in service_path:
            # If service_path looks like a service_name for V4, convert it
            service_path = self.get_service_path(service_path)

        if not service_path:
            raise ValueError("No service path or service name provided")

        url = f"{self.build_service_url(service_path)}/$metadata"

        # Define parameters with sap-client explicitly included
        params = {"sap-client": self.client_id}

        # Use direct requests call to avoid error detection logic that might misinterpret metadata XML
        try:
            logger.debug(f"Making GET request to {url} for metadata")

            response = requests.get(
                url=url,
                auth=self._get_auth(),
                params=params,
                headers={
                    "Accept": "application/xml",
                    "Content-Type": "application/xml",
                },
                timeout=self.timeout,
            )

            # For metadata, only check HTTP status codes, not content
            response.raise_for_status()

            # Verify we got XML content
            content_type = response.headers.get("Content-Type", "")
            if not any(
                xml_type in content_type for xml_type in ["application/xml", "text/xml"]
            ):
                logger.warning(
                    f"Expected XML content for metadata, got: {content_type}"
                )

            return response.text

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_detail = e.response.text[:500] if e.response.text else ""

            logger.error(
                f"HTTP error fetching metadata: Status {status_code}, Detail: {error_detail}"
            )

            if status_code == 404:
                raise SAPResourceNotFoundException(
                    f"Metadata not found: {error_detail}"
                )
            elif status_code == 401:
                raise SAPAuthenticationException(
                    f"Authentication failed: {error_detail}"
                )
            elif status_code == 403:
                raise SAPAuthorizationException(f"Access denied: {error_detail}")
            else:
                raise SAPServerException(
                    f"Error fetching metadata", status_code, error_detail
                )

        except Exception as e:
            logger.error(f"Error fetching raw metadata: {e}")
            raise

    def get_entity_count(
        self,
        service_path: Optional[str] = None,
        entity_set: Optional[str] = None,
        filter_query: Optional[str] = None,
    ) -> int:
        """
        Get count of entities (works for both V2 and V4)

        Args:
            service_path: The specific OData service path or service name (optional if service_name was provided at initialization)
            entity_set: Name of the entity set
            filter_query: OData filter query

        Returns:
            Count of entities
        """
        # If no service_path is provided, try to use service_name
        if not service_path and self.service_name:
            service_path = self.get_service_path()
        elif service_path and self.odata_version == "v4" and "/" not in service_path:
            # If service_path looks like a service_name for V4, convert it
            service_path = self.get_service_path(service_path)

        if not service_path:
            raise ValueError("No service path or service name provided")

        if not entity_set:
            raise ValueError("No entity set provided")

        if self.odata_version == "v4":
            url = f"{self.build_service_url(service_path)}/{entity_set}/$count"
        else:  # V2
            url = f"{self.build_service_url(service_path)}/{entity_set}/$count"

        params = {}
        if filter_query:
            params["$filter"] = filter_query

        try:
            response = self._make_request("GET", url, params=params)
            # For $count endpoints, response should be plain text with a number
            response_text = response.text.strip()
            if response_text.isdigit():
                return int(response_text)
            else:
                logger.error(f"Invalid count response: {response_text}")
                raise SAPAPIException(
                    f"Invalid count response from SAP: {response_text}"
                )

        except (
            SAPResourceNotFoundException,
            SAPAuthorizationException,
            SAPAuthenticationException,
        ):
            # Re-raise specific SAP exceptions
            raise
        except SAPAPIException as sap_e:
            # Log the specific SAP error and try fallback for V2
            logger.error(f"SAP API error getting count: {sap_e}")
            if self.odata_version == "v2":
                logger.info("Attempting V2 fallback with $inlinecount")
                try:
                    params = {"$inlinecount": "allpages", "$top": 1}
                    if filter_query:
                        params["$filter"] = filter_query

                    fallback_url = (
                        f"{self.build_service_url(service_path)}/{entity_set}"
                    )
                    response = self._make_request("GET", fallback_url, params=params)
                    data = response.json()

                    # V2 returns count in "d.__count" property
                    if "d" in data and "__count" in data["d"]:
                        return int(data["d"]["__count"])
                    elif "d" in data and "results" in data["d"]:
                        # If no __count but we have results, return length
                        return len(data["d"]["results"])
                    else:
                        logger.error(
                            f"V2 fallback failed - unexpected response structure: {data}"
                        )
                        raise SAPAPIException(
                            f"Unable to get count from SAP service. Original error: {sap_e}"
                        )

                except Exception as fallback_e:
                    logger.error(f"V2 fallback also failed: {fallback_e}")
                    raise SAPAPIException(
                        f"Unable to get count from SAP service. Count endpoint error: {sap_e}, Fallback error: {fallback_e}"
                    )
            else:
                # For V4, re-raise the original error
                raise
        except Exception as e:
            logger.error(f"Unexpected error getting entity count: {e}")
            raise SAPAPIException(f"Unexpected error getting count from SAP: {e}")

    def get_data(
        self,
        service_path: Optional[str] = None,
        entity_set: Optional[str] = None,
        entity_key: Optional[str] = None,
        navigation_property: Optional[str] = None,
        filter_query: Optional[str] = None,
        select_query: Optional[str] = None,
        expand_query: Optional[str] = None,
        order_by: Optional[str] = None,
        skip: Optional[int] = None,
        top: Optional[int] = None,
        count: bool = False,
        next_link: Optional[str] = None,
    ) -> Dict:
        """
        Generic method to fetch data from any SAP OData API (V2 or V4)

        Args:
            service_path: The specific OData service path or service name (optional if service_name was provided at initialization)
            entity_set: Name of the entity set
            entity_key: Entity key(s) for specific entity access (e.g., "subscriptionrefid='SR100062',weborderid='96695165'")
            navigation_property: Navigation property to access (e.g., "Set")
            filter_query: OData $filter query string
            select_query: OData $select query string
            expand_query: OData $expand query string
            order_by: OData $orderby query string
            skip: Number of records to skip
            top: Maximum number of records to return
            count: Whether to include count in response
            next_link: Next link for pagination

        Returns:
            Dictionary containing API response data
        """
        # If no service_path is provided, try to use service_name
        if not service_path and self.service_name:
            service_path = self.get_service_path()
        elif service_path and self.odata_version == "v4" and "/" not in service_path:
            # If service_path looks like a service_name for V4, convert it
            service_path = self.get_service_path(service_path)

        if not service_path:
            raise ValueError("No service path or service name provided")

        if not entity_set:
            raise ValueError("No entity set provided")

        if next_link:
            url = (
                f"{self.hostname}{next_link}"
                if not next_link.startswith("http")
                else next_link
            )
            params = {}
            # Ensure sap-client is present in next_link URL or add it
            if "sap-client=" not in url:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}sap-client={self.client_id}"

            # For V2, ensure $format=json is present
            if self.odata_version == "v2" and "$format=json" not in url:
                url = f"{url}&$format=json"
        else:
            url = f"{self.build_service_url(service_path)}/{entity_set}"

            # Add entity key if provided
            if entity_key:
                # Handle different key formats
                if not entity_key.startswith("(") and not entity_key.endswith(")"):
                    # Wrap in parentheses if not already wrapped
                    url += f"({entity_key})"
                else:
                    url += entity_key

            # Add navigation property if provided
            if navigation_property:
                url += f"/{navigation_property}"

            params = {}

            if filter_query:
                params["$filter"] = filter_query
            if select_query:
                params["$select"] = select_query
            if expand_query:
                params["$expand"] = expand_query
            if order_by:
                params["$orderby"] = order_by
            if skip is not None:
                params["$skip"] = skip
            if top is not None:
                params["$top"] = top

            # Handle count differently for V2 and V4
            if count:
                if self.odata_version == "v4":
                    params["$count"] = "true"
                else:  # V2
                    params["$inlinecount"] = "allpages"

            # For V2, always include $format=json to ensure JSON response
            if self.odata_version == "v2":
                params["$format"] = "json"

            # Always include sap-client parameter in the query parameters
            params["sap-client"] = self.client_id

        try:
            response = self._make_request("GET", url, params=params)
            data = response.json()

            # Transform V2 response to be similar to V4 structure for easier handling
            if self.odata_version == "v2" and "d" in data:
                if "results" in data["d"]:
                    # Normalize V2 response to match V4 format
                    normalized = {
                        "value": data["d"]["results"],
                    }

                    # Handle inline count for V2
                    if "__count" in data["d"]:
                        normalized["@odata.count"] = int(data["d"]["__count"])

                    # Handle pagination for V2
                    if "__next" in data["d"]:
                        normalized["@odata.nextLink"] = data["d"]["__next"]

                    return normalized
                else:
                    # Single entity result
                    return {"value": [data["d"]]}

            return data

        except (
            SAPResourceNotFoundException,
            SAPAuthorizationException,
            SAPAuthenticationException,
            SAPAPIException,
        ):
            # Re-raise specific SAP exceptions with more context
            raise
        except json.JSONDecodeError as json_e:
            logger.error(f"Invalid JSON response from SAP API {url}: {json_e}")
            logger.error(
                f"Response content: {response.text[:500] if 'response' in locals() else 'No response'}"
            )
            raise SAPAPIException(f"Invalid JSON response from SAP API: {json_e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching data from {url}: {e}")
            # Provide more context about the request that failed
            raise SAPAPIException(
                f"Failed to fetch data from SAP service '{entity_set}': {e}"
            )

    def fetch_all_data(
        self,
        service_path: Optional[str] = None,
        entity_set: Optional[str] = None,
        filter_query: Optional[str] = None,
        select_query: Optional[str] = None,
        output_file: Optional[str] = None,
        batch_size: int = 10000,
    ) -> List[Dict]:
        """
        Fetch all data with pagination handling (works for both V2 and V4)

        Args:
            service_path: The specific OData service path or service name (optional if service_name was provided at initialization)
            entity_set: Name of the entity set
            filter_query: OData filter query
            select_query: OData select query
            output_file: CSV file to save results incrementally
            batch_size: Records per batch for incremental saving

        Returns:
            List of all records
        """
        # If no service_path is provided, try to use service_name
        if not service_path and self.service_name:
            service_path = self.get_service_path()
        elif service_path and self.odata_version == "v4" and "/" not in service_path:
            # If service_path looks like a service_name for V4, convert it
            service_path = self.get_service_path(service_path)

        if not service_path:
            raise ValueError("No service path or service name provided")

        if not entity_set:
            raise ValueError("No entity set provided")

        all_data = []
        next_link = None
        total_fetched = 0
        batch_id = 1

        # Get total record count
        total_records = self.get_entity_count(service_path, entity_set, filter_query)
        logger.debug(f"Total records: {total_records}")

        if total_records == 0:
            logger.debug("No records found")
            return []

        # Fetch data with pagination
        while True:
            logger.debug(f"Fetching batch {batch_id}")

            # For V2, we use $skip and $top for pagination if no next_link
            if self.odata_version == "v2" and next_link is None and total_fetched > 0:
                data = self.get_data(
                    service_path=service_path,
                    entity_set=entity_set,
                    filter_query=filter_query,
                    select_query=select_query,
                    skip=total_fetched,
                    top=1000,  # Typical SAP OData V2 page size
                )
            else:
                data = self.get_data(
                    service_path=service_path,
                    entity_set=entity_set,
                    filter_query=filter_query,
                    select_query=select_query,
                    next_link=next_link,
                )

            if not data or "value" not in data:
                logger.debug("No more data available")
                break

            records = data["value"]
            all_data.extend(records)
            total_fetched += len(records)
            batch_id += 1

            # Check for pagination link
            if self.odata_version == "v4":
                next_link = data.get("@odata.nextLink")
            else:  # V2
                next_link = data.get(
                    "@odata.nextLink"
                )  # We normalized this in get_data

            # For V2, if no explicit next link but we haven't reached total count, continue with $skip
            if (
                next_link is None
                and self.odata_version == "v2"
                and total_fetched < total_records
            ):
                # We'll use skip parameter in the next iteration
                pass
            elif next_link is None:
                break  # Exit loop if no more data

        logger.info(f"Fetched {total_fetched} records")
        return all_data

    def get_service_path(self, service_name: Optional[str] = None) -> str:
        """
        Generate the full service path for OData V4 from a service name

        Args:
            service_name: The service name (if not provided, will use the one from initialization)

        Returns:
            Complete service path for the OData service

        Raises:
            ValueError: If no service name is provided and none was set during initialization
        """
        # Use provided service_name or the one from init
        service_name_to_use = service_name or self.service_name

        if not service_name_to_use:
            raise ValueError(
                "No service name provided. Please provide a service name or set it during initialization."
            )

        if self.odata_version == "v4":
            # URL pattern: /sap/opu/odata4/sap/{namespace}/srvd_a2x/sap/{service_name}/0001/
            # Use service_namespace if provided, otherwise fallback to service_name
            namespace = self.service_namespace or service_name_to_use
            return f"{namespace}/srvd_a2x/sap/{service_name_to_use}/0001"
        else:
            # For V2, service_name is the service_path
            return service_name_to_use
