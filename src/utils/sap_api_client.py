from http.client import HTTPException
import os
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import json
from typing import Dict, List, Optional, Literal

from .logger import logger
from .http_client import get_http_client_manager, metadata_cache
from ..config import SAP_SYSTEMS

# Load environment variables
load_dotenv()

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
        service_name: str,
        client_id: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,    
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
        self.client_id = client_id or SAP_SYSTEMS[self.system_id]["client_id"]
        self.username = username or os.getenv("SAP_USERNAME")
        self.password = password or os.getenv("SAP_PASSWORD")
        
        self.timeout = timeout
        self.odata_version = odata_version
        self.service_name = service_name
        self.service_namespace = service_namespace 

        if self.system_id not in SAP_SYSTEMS:
            raise ValueError(f"System ID '{self.system_id}' not found in configuration")
            
        if not self.username or not self.password:
            raise ValueError("Please provide SAP Credentials")

        self.hostname = SAP_SYSTEMS[self.system_id]["hostname"]

        # Set base path according to OData version if not provided
        if base_path is None:
            self.base_path = (
                "/sap/opu/odata4/sap" if odata_version == "v4" else "/sap/opu/odata/sap"
            )
        else:
            self.base_path = base_path

        # Initialize HTTP client manager for connection pooling
        self.http_manager = get_http_client_manager()
        
        logger.info(f"SAP API Client initialized: {self.hostname} ({odata_version}) Client: {self.client_id}")
        if service_name:
            logger.debug(f"Service: {service_name}")
            if odata_version == "v4":
                service_path = self.get_service_path()
                logger.debug(f"Service path: {service_path}")

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

    def _make_request_with_pool(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> requests.Response:
        """Make HTTP request using connection pooled client (simple version)"""
        try:
            import base64
            
            # Get the sync HTTP client from manager
            http_client = self.http_manager.get_sync_client()
            
            # Prepare headers with Basic Auth
            request_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            if headers:
                request_headers.update(headers)
            
            # Add Basic Auth header
            if self.username and self.password:
                auth_string = f"{self.username}:{self.password}"
                encoded_auth = base64.b64encode(auth_string.encode()).decode()
                request_headers["Authorization"] = f"Basic {encoded_auth}"
            
            # Prepare params
            if params is None:
                params = {}
            if "sap-client" not in params:
                params["sap-client"] = self.client_id
            
            logger.debug(f"Making {method} request to {url} (using connection pool)")
            
            # Make the request with httpx
            response = http_client.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=request_headers,
                timeout=self.timeout,
            )
            
            # Convert httpx response to requests-like response
            return self._convert_httpx_to_requests(response)
            
        except Exception as e:
            logger.debug(f"Connection pool request failed, falling back to requests: {e}")
            # Fallback to regular requests
            return self._make_request_fallback(method, url, params, data, headers)

    def _convert_httpx_to_requests(self, httpx_response):
        """Convert httpx Response to requests.Response-like object for compatibility"""
        import requests
        from unittest.mock import Mock
        
        # Create a mock response that behaves like requests.Response
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = httpx_response.status_code
        mock_response.headers = dict(httpx_response.headers)
        mock_response.text = httpx_response.text
        mock_response.content = httpx_response.content
        mock_response.url = str(httpx_response.url)
        
        # Add json() method
        def json_method():
            import json
            return json.loads(httpx_response.text)
        mock_response.json = json_method
        
        # Add raise_for_status() method
        def raise_for_status():
            if httpx_response.status_code >= 400:
                import requests
                raise requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status = raise_for_status
        
        return mock_response

    def _make_request_fallback(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> requests.Response:
        """Fallback method using standard requests library"""
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

        logger.debug(f"Making {method} request to {url} (fallback)")
        
        return requests.request(
            method=method,
            url=url,
            auth=self._get_auth(),
            params=params,
            json=data,
            headers=default_headers,
            timeout=self.timeout,
        )

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> requests.Response:
        """Make HTTP request to SAP API with connection pooling and improved error handling"""
        
        # Try connection pooled request first, fallback to requests if needed
        try:
            return self._make_request_with_pool(method, url, params, data, headers)
        except Exception as e:
            logger.debug(f"Pooled request failed, using fallback: {e}")
            return self._make_request_fallback(method, url, params, data, headers)

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

    def get_raw_metadata(self, service_path: Optional[str] = None) -> str:
        """
        Fetch raw metadata XML from an OData service (V2 or V4) with caching

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

        # Check cache first (metadata doesn't change often)
        cache_key = f"metadata_{self.system_id}_{service_path}_{self.odata_version}"
        cached_metadata = metadata_cache.get(cache_key)
        if cached_metadata:
            logger.debug(f"Using cached metadata for {service_path}")
            return cached_metadata

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

            # Cache the metadata for future requests
            metadata_cache.set(cache_key, response.text)
            logger.debug(f"Cached metadata for {service_path}")
            
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
