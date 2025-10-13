"""
Common utilities and decorators for SAP services
"""
import logging
import os, sys
from typing import Callable, TypeVar
from functools import wraps
from fastapi import HTTPException

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from src.utils.sap_api_client import (
    SAPAPIException, 
    SAPAuthenticationException, 
    SAPAuthorizationException, 
    SAPResourceNotFoundException,
    SAPServerException
)

logger = logging.getLogger(__name__)

T = TypeVar('T')

def handle_sap_exceptions(operation_name: str = "SAP operation"):
    """
    Decorator to handle SAP exceptions and convert them to HTTPExceptions
    
    Args:
        operation_name: Name of the operation for logging purposes
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPExceptions as-is
                raise
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except SAPAuthenticationException as e:
                raise HTTPException(status_code=401, detail="SAP authentication failed - check credentials")
            except SAPAuthorizationException as e:
                raise HTTPException(status_code=403, detail="SAP authorization failed - insufficient permissions")
            except SAPResourceNotFoundException as e:
                raise HTTPException(status_code=404, detail="SAP resource not found")
            except SAPServerException as e:
                logger.error(f"SAP server error details: status_code={e.status_code}, error_detail={e.error_detail}")
                raise HTTPException(status_code=502, detail=f"SAP server error: {e.error_detail or e.message}")
            except SAPAPIException as e:
                raise HTTPException(status_code=500, detail=f"SAP API error: {e.message}")
            except Exception as e:
                logger.error(f"Error in {operation_name}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        return wrapper
    return decorator
