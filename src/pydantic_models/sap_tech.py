"""
Pydantic models for SAP technical metadata operations
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Optional, Any


class SAPServiceConfig(BaseModel):
    """Configuration model for SAP service details used by tools"""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "service_name": "ZSD_TABLE_SCHEMA",
                    "service_namespace": "ZSB_TABLE_SCHEMA",
                    "entity_name": "TableSchema",
                    "odata_version": "v4",
                    "http_method": "GET",
                },
                {
                    "service_name": "ZSD_PRODUCTS",
                    "entity_name": "Products",
                    "odata_version": "v4",
                    "http_method": "GET",
                },
            ]
        },
    )

    service_name: str = Field(
        ..., description="SAP OData service name (e.g., 'ZSD_TABLE_SCHEMA')"
    )
    service_namespace: Optional[str] = Field(
        None, description="Service namespace for OData v4 (e.g., 'ZSB_TABLE_SCHEMA')"
    )
    entity_name: str = Field(
        ..., description="Entity name or endpoint path (e.g., 'TableSchema')"
    )
    odata_version: str = Field(
        default="v4", description="OData version", pattern="^(v2|v4)$"
    )
    http_method: str = Field(
        default="GET",
        description="Default HTTP method for this service",
        pattern="^(GET|POST|PUT|PATCH|DELETE)$",
    )


class MetadataRequest(BaseModel):
    """Request model for metadata retrieval"""

    service_name: str = Field(..., description="SAP OData service name")
    service_namespace: Optional[str] = Field(
        None, description="Service namespace (if different from service name)"
    )
    odata_version: Optional[str] = Field(
        "v4", description="OData version: v2 or v4", pattern="^(v2|v4)$"
    )
    system_id: Optional[str] = Field(
        None, description="SAP system ID (e.g., 'RHA', 'RHP')"
    )


class MetadataResponse(BaseModel):
    """SAP OData service metadata response model"""

    model_config = ConfigDict(populate_by_name=True)

    service_name: str = Field(..., description="Service name")
    service_namespace: str = Field(..., description="Service namespace")
    odata_version: str = Field(..., description="OData version (v2 or v4)")
    metadata_xml: str = Field(..., description="Complete metadata XML content")
    message: Optional[str] = Field(
        None, description="Optional message for user information"
    )


class GenericAPIRequest(BaseModel):
    """Generic SAP API request model for any HTTP method"""

    model_config = ConfigDict(populate_by_name=True)

    system_id: str = Field(
        ..., description="Target SAP system ID, D2A, DHA, RHA, Q2A, etc."
    )
    http_method: str = Field(
        ...,
        description="HTTP method used (GET, POST, PUT, PATCH, DELETE) - defaults from service config",
    )
    service_name: Optional[str] = Field(
        None, description="Service name - defaults from service config"
    )
    service_namespace: Optional[str] = Field(
        None,
        description="Service namespace, needed in case of oData v4 - defaults from service config",
    )
    entity_name: str = Field(
        ...,
        description="Entity name or custom path - defaults from service config",
        alias="entity_name",
    )
    odata_version: str = Field(
        ..., description="OData version (v2 or v4) - defaults from service config"
    )
    request_body: Optional[Dict[str, Any]] = Field(
        None, description="Request body data (for POST/PUT/PATCH)"
    )
    query_parameters: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="""
            Query parameters, supported values:         
            "filter",
            "select",
            "expand",
            "orderby",
            "top",
            "skip",
            "count",
            "search",
            "format",
            "inlinecount"

        Examples:
        query_parameters={
            "filter": "SubsRefId eq 'SUB123456'",
            "select": "SubsRefId,WebOrderId,OrderedProductName,ActivationStatus",
            "expand": "_ConfigParams($filter=(ConfigName eq 'CIS_CC_BILL_MODEL' or ConfigName eq 'CIS_CC_BILLIMMEDIATE')"
        }
        
        query_parameters={
            "filter": "ActivationStatus eq 'E' and ItemCreatedAt ge 2024-01-01T00:00:00Z and ItemCreatedAt le 2024-12-31T23:59:59Z",
            "orderby": "ItemCreatedAt desc",
            "top": "100"
        }                
        """,
    )
    client_id: Optional[int] = Field(
        None, description="Optional client ID for SAP system"
    )
    username: Optional[str] = Field(
        None, description="Optional username for basic authentication"
    )
    password: Optional[str] = Field(
        None, description="Optional password for basic authentication"
    )


class GenericAPIResponse(BaseModel):
    """Generic SAP API response model for any HTTP method"""

    model_config = ConfigDict(populate_by_name=True)

    http_method: str = Field(
        ..., description="HTTP method used (GET, POST, PUT, PATCH, DELETE)"
    )
    service_name: str = Field(..., description="Service name")
    service_namespace: Optional[str] = Field(
        None, description="Service Namespace, Optional only in case of v2 APIs"
    )
    entity_name: str = Field(
        ..., description="Entity name or custom path", alias="entity_name"
    )
    odata_version: str = Field(..., description="OData version (v2 or v4)")
    request_url: str = Field(..., description="Complete request URL")
    status_code: int = Field(..., description="HTTP response status code")
    success: bool = Field(..., description="Whether the request was successful")
    raw_response: Optional[Dict[str, Any]] = Field(
        None, description="Complete raw response (for successful requests)"
    )
    request_body: Optional[Dict[str, Any]] = Field(
        None, description="Request body data (for POST/PUT/PATCH)"
    )
    query_parameters: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Query parameters used"
    )
    response_headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Response headers"
    )
    execution_time_ms: Optional[int] = Field(
        None, description="Request execution time in milliseconds"
    )
    record_count: Optional[int] = Field(
        None, description="Number of records (for GET operations)"
    )
    error_details: Optional[str] = Field(
        None, description="Error details (for failed requests)"
    )
    message: Optional[str] = Field(
        None, description="Optional message for user information"
    )
