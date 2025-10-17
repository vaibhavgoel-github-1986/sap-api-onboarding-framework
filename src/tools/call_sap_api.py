import sys, os
from typing import Literal, Optional 
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from src.utils.sap_common import handle_sap_exceptions
from src.models.sap_tech import (
    GenericAPIResponse,
)
from src.utils.sap_generic_service import SAPGenericService

# Load environment variables
load_dotenv()

@handle_sap_exceptions(operation_name="Call SAP Generic API")
def call_sap_api_generic(
    http_method: str,
    service_name: str,
    entity_name: str,
    system_id: str,
    service_namespace: Optional[str] = None,
    odata_version: Literal["v2", "v4"] = "v4",
    query_parameters: Optional[dict] = None,
    request_body: Optional[dict] = None,
    client_id: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> GenericAPIResponse:
    """
    Delegate to the generic service for unified API operations
    """
    return SAPGenericService().call_sap_api_generic(
        http_method=http_method,
        service_name=service_name,
        entity_name=entity_name,
        service_namespace=service_namespace,
        odata_version=odata_version,
        query_parameters=query_parameters,
        request_body=request_body,
        system_id=system_id,
        client_id=client_id,
        username=username,
        password=password
    )
