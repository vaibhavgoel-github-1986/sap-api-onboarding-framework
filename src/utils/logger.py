import logging
import sys
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def __init__(self, service_name: str = "SAP-Tools-API", version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        
        # Base structured log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "version": self.version,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "thread_id": record.thread,
            "process_id": record.process,
        }
        
        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = getattr(record, 'correlation_id')
        
        # Add request ID if available  
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = getattr(record, 'request_id')
            
        # Add user ID if available
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = getattr(record, 'user_id')
            
        # Add custom fields if available
        if hasattr(record, 'extra_fields'):
            log_entry.update(getattr(record, 'extra_fields'))
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        return json.dumps(log_entry, ensure_ascii=False)


class StructuredLogger:
    """Enhanced structured logger for SAP Tools API."""
    
    def __init__(
        self, 
        name: str = "SAP-Tools-API",
        level: str = "INFO",
        service_name: str = "SAP-Tools-API",
        version: str = "1.0.0",
        enable_json: Optional[bool] = True
    ):
        self.name = name
        self.service_name = service_name
        self.version = version

        self.enable_json = enable_json
        self.logger = self._setup_logger(level)
    
    def _setup_logger(self, level: str) -> logging.Logger:
        """Setup the logger with appropriate formatting."""
        logger = logging.getLogger(self.name)
        
        # Set log level
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        # Clear existing handlers
        if logger.hasHandlers():
            logger.handlers.clear()
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Choose formatter based on environment
        if self.enable_json:
            formatter = StructuredFormatter(self.service_name, self.version)
        else:
            # Human-readable format for development
            formatter = logging.Formatter(
                fmt='[%(levelname)s] %(asctime)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.propagate = False
        
        return logger
    
    def _log_with_context(
        self, 
        level: str, 
        message: str, 
        extra_fields: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """Internal method to log with additional context."""
        extra = {}
        
        if extra_fields:
            extra['extra_fields'] = extra_fields
        if correlation_id:
            extra['correlation_id'] = correlation_id
        if request_id:
            extra['request_id'] = request_id
        if user_id:
            extra['user_id'] = user_id
            
        # Add any additional kwargs as extra fields
        if kwargs:
            extra.setdefault('extra_fields', {}).update(kwargs)
        
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log_with_context("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log_with_context("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log_with_context("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log_with_context("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self._log_with_context("CRITICAL", message, **kwargs)


def setup_logger(
    name: str = "SAP-Tools-API", 
    level: str = "INFO",
    enable_json: Optional[bool] = None
) -> StructuredLogger:
    """
    Setup structured logger with enhanced capabilities.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Force JSON output (auto-detects if None)
    
    Returns:
        Configured StructuredLogger instance
    """
    return StructuredLogger(name=name, level=level, enable_json=enable_json)


# Create default logger instances
logger = setup_logger()

# Legacy compatibility functions
def debug(message: str):
    logger.debug(message)

def info(message: str):
    logger.info(message)

def warning(message: str):
    logger.warning(message)

def error(message: str):
    logger.error(message)

def critical(message: str):
    logger.critical(message)


# Enhanced structured logging functions
def log_api_request(
    request=None,  # FastAPI Request object or manual parameters
    method: Optional[str] = None, 
    url: Optional[str] = None, 
    user_query: Optional[str] = None, 
    system_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    request_body: Optional[dict] = None
):
    """
    Log API request with structured data.
    
    Args:
        request: FastAPI Request object (auto-extracts method, url, headers, etc.)
        method: HTTP method (if not using request object)
        url: Request URL (if not using request object)
        user_query: User query from request body
        system_id: SAP system ID
        request_id: Unique request ID (auto-generated if not provided)
        user_id: User ID from headers or auth
        request_body: Request body content
    """
    from fastapi import Request
    import uuid
    
    # Auto-extract from FastAPI Request object
    if request and isinstance(request, Request):
        method = method or request.method
        url = url or str(request.url)
        request_id = request_id or request.headers.get('x-request-id', str(uuid.uuid4()))
        user_id = user_id or request.headers.get('x-user-id') or request.headers.get('authorization', '').split(' ')[-1] if request.headers.get('authorization') else None
        
        # Try to extract user_query from request body if it's a QueryRequest
        if not user_query and hasattr(request, 'json') and request_body:
            user_query = request_body.get('user_query') if isinstance(request_body, dict) else getattr(request_body, 'user_query', None)
    
    # Generate request_id if not provided
    if not request_id:
        request_id = str(uuid.uuid4())
    
    logger.info(
        "API request initiated",
        extra_fields={
            "event_type": "api_request",
            "http_method": method,
            "url": url,
            "user_query": user_query,
            "system_id": system_id,
            "request_body_keys": list(request_body.keys()) if isinstance(request_body, dict) else None
        },
        request_id=request_id,
        user_id=user_id
    )


def log_api_response(
    response=None,  # FastAPI Response object or our Pydantic response models
    status_code: Optional[int] = None, 
    execution_time_ms: Optional[int] = None, 
    success: Optional[bool] = None, 
    record_count: Optional[int] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    error_details: Optional[str] = None
):
    """
    Log API response with structured data.
    
    Args:
        response: FastAPI Response object or Pydantic response model (auto-extracts data)
        status_code: HTTP status code (if not using response object)
        execution_time_ms: Request execution time
        success: Whether request was successful
        record_count: Number of records returned
        request_id: Request ID to correlate with request log
        user_id: User ID
        error_details: Error details if request failed
    """
    from fastapi import Response
    
    # Auto-extract from response objects
    if response:
        # Handle Pydantic response models
        if hasattr(response, 'model_dump'):
            response_data = response.model_dump()
            
            # Generic handling for any response model
            success = success if success is not None else response_data.get('success', True)
            status_code = status_code or response_data.get('status_code')
            execution_time_ms = execution_time_ms or response_data.get('execution_time_ms')
            record_count = record_count or response_data.get('record_count') or response_data.get('entity_count')
            error_details = error_details or response_data.get('error_details') or response_data.get('error')
                
        # Handle FastAPI Response objects
        elif isinstance(response, Response):
            status_code = status_code or response.status_code
            success = success if success is not None else (200 <= response.status_code < 300)
    
    # Default values
    status_code = status_code or 200
    success = success if success is not None else (200 <= status_code < 300)
    
    level = "info" if success else "error"
    message = f"API response completed - Status: {status_code}, Duration: {execution_time_ms}ms"
    
    getattr(logger, level)(
        message,
        extra_fields={
            "event_type": "api_response",
            "status_code": status_code,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "record_count": record_count,
            "error_details": error_details
        },
        request_id=request_id,
        user_id=user_id
    )


def log_sap_operation(
    operation: Optional[str] = None,
    system_id: Optional[str] = None,
    service_name: Optional[str] = None,
    entity_name: Optional[str] = None,
    success: Optional[bool] = None,
    execution_time_ms: Optional[int] = None,
    record_count: Optional[int] = None,
    error_message: Optional[str] = None,
    request_id: Optional[str] = None,
    sap_request=None,  # GenericAPIRequest object
    sap_response=None  # GenericAPIResponse object
):
    """
    Log SAP system operations with structured data.
    
    Args:
        operation: SAP operation type (READ, CREATE, UPDATE, DELETE)
        system_id: SAP system ID
        service_name: OData service name
        entity_name: Entity name
        success: Whether operation was successful
        execution_time_ms: Operation execution time
        record_count: Number of records affected
        error_message: Error message if operation failed
        request_id: Request ID for correlation
        sap_request: GenericAPIRequest object (auto-extracts data)
        sap_response: GenericAPIResponse object (auto-extracts data)
    """
    
    # Auto-extract from SAP request object
    if sap_request and hasattr(sap_request, 'model_dump'):
        request_data = sap_request.model_dump()
        
        # Generic handling for request models
        system_id = system_id or request_data.get('system_id')
        service_name = service_name or request_data.get('service_name')
        entity_name = entity_name or request_data.get('entity_name')
        operation = operation or request_data.get('http_method', 'READ')
    
    # Auto-extract from SAP response object  
    if sap_response and hasattr(sap_response, 'model_dump'):
        response_data = sap_response.model_dump()
        
        # Generic handling for response models
        system_id = system_id or response_data.get('system_id')
        service_name = service_name or response_data.get('service_name')
        entity_name = entity_name or response_data.get('entity_name')
        operation = operation or response_data.get('http_method', 'READ')
        success = success if success is not None else response_data.get('success')
        execution_time_ms = execution_time_ms or response_data.get('execution_time_ms')
        record_count = record_count or response_data.get('record_count') or response_data.get('entity_count')
        error_message = error_message or response_data.get('error_details')
    
    # Default values
    success = success if success is not None else True
    operation = operation or 'UNKNOWN'
    
    level = "info" if success else "error"
    message = f"SAP {operation} {'completed' if success else 'failed'} - {system_id}/{service_name}/{entity_name}"
    
    getattr(logger, level)(
        message,
        extra_fields={
            "event_type": "sap_operation",
            "operation": operation,
            "system_id": system_id,
            "service_name": service_name,
            "entity_name": entity_name,
            "success": success,
            "execution_time_ms": execution_time_ms,
            "record_count": record_count,
            "error_message": error_message
        },
        request_id=request_id
    )


def log_authentication_event(
    event_type: str,
    user_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    request_id: Optional[str] = None
):
    """Log authentication events with structured data."""
    level = "info" if success else "warning"
    message = f"Authentication {event_type} {'successful' if success else 'failed'}"
    
    getattr(logger, level)(
        message,
        extra_fields={
            "event_type": "authentication",
            "auth_event": event_type,
            "success": success,
            "error_message": error_message
        },
        user_id=user_id,
        request_id=request_id
    )


def log_error_with_context(
    error_msg: str, 
    context: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Log error with additional context."""
    logger.error(
        error_msg,
        extra_fields={
            "event_type": "error",
            "context": context or {}
        },
        correlation_id=correlation_id,
        request_id=request_id,
        user_id=user_id
    )


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = "ms",
    tags: Optional[Dict[str, str]] = None,
    request_id: Optional[str] = None
):
    """Log performance metrics with structured data."""
    logger.info(
        f"Performance metric: {metric_name} = {value} {unit}",
        extra_fields={
            "event_type": "performance_metric",
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "tags": tags or {}
        },
        request_id=request_id
    )


def log_business_event(
    event_name: str,
    event_data: Dict[str, Any],
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
):
    """Log business events with structured data."""
    logger.info(
        f"Business event: {event_name}",
        extra_fields={
            "event_type": "business_event",
            "event_name": event_name,
            "event_data": event_data
        },
        user_id=user_id,
        request_id=request_id
    )

# End of structured logging module

# Convenience functions for automatic logging
def log_fastapi_request_response(request, response=None, request_body=None, execution_time_ms=None):
    """
    Convenience function to log both request and response automatically.
    
    Usage in FastAPI routes:
    ```python
    @router.post("/endpoint")
    async def my_endpoint(request: Request, body: QueryRequest):
        start_time = time.time()
        
        # Your logic here
        response = process_request(body)
        
        execution_time = int((time.time() - start_time) * 1000)
        log_fastapi_request_response(request, response, body.model_dump(), execution_time)
        return response
    ```
    """
    import uuid
    
    # Generate request ID for correlation
    request_id = request.headers.get('x-request-id', str(uuid.uuid4()))
    
    # Log request
    log_api_request(
        request=request,
        request_body=request_body,
        request_id=request_id
    )
    
    # Log response if provided
    if response is not None:
        log_api_response(
            response=response,
            execution_time_ms=execution_time_ms,
            request_id=request_id
        )
    
    return request_id


def log_sap_request_response(sap_request, sap_response=None, request_id=None):
    """
    Convenience function to log SAP operations automatically.
    
    Usage:
    ```python
    # Log both request and response
    log_sap_request_response(generic_request, generic_response, request_id)
    
    # Or just the request
    log_sap_request_response(generic_request, request_id=request_id)
    ```
    """
    # Log SAP operation
    log_sap_operation(
        sap_request=sap_request,
        sap_response=sap_response,
        request_id=request_id
    )