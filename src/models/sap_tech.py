"""
Pydantic models for SAP technical metadata operations
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any


class MetadataResponse(BaseModel):
    """SAP OData service metadata response model"""
    
    model_config = ConfigDict(populate_by_name=True)
    
    service_name: str = Field(..., description="Service name")
    service_namespace: str = Field(..., description="Service namespace")
    odata_version: str = Field(..., description="OData version (v2 or v4)")
    metadata_xml: str = Field(..., description="Complete metadata XML content")
    entity_count: int = Field(..., description="Number of entity types found")
    message: Optional[str] = Field(None, description="Optional message for user information")


class SampleDataResponse(BaseModel):
    """SAP OData service sample data response model"""
    
    model_config = ConfigDict(populate_by_name=True)
    
    service_name: str = Field(..., description="Service name")
    service_namespace: str = Field(..., description="Service namespace")
    entity_set: str = Field(..., description="Entity set name")
    odata_version: str = Field(..., description="OData version (v2 or v4)")
    raw_response: Dict[str, Any] = Field(..., description="Complete raw OData response with original structure")
    record_count: int = Field(..., description="Number of records returned in this response")
    total_records: Optional[int] = Field(None, description="Total number of records available in entity set")
    fields_found: List[str] = Field(default_factory=list, description="List of field names found in the sample data")
    query_parameters: Optional[Dict[str, str]] = Field(default_factory=dict, description="Query parameters used in the request")
    message: Optional[str] = Field(None, description="Optional message for user information")


class GenericAPIResponse(BaseModel):
    """Generic SAP API response model for any HTTP method"""
    
    model_config = ConfigDict(populate_by_name=True)
    
    http_method: str = Field(..., description="HTTP method used (GET, POST, PUT, PATCH, DELETE)")
    service_name: str = Field(..., description="Service name")
    service_namespace: str = Field(..., description="Service namespace")
    entity_name: str = Field(..., description="Entity name or custom path", alias="entity_name")
    odata_version: str = Field(..., description="OData version (v2 or v4)")
    request_url: str = Field(..., description="Complete request URL")
    status_code: int = Field(..., description="HTTP response status code")
    success: bool = Field(..., description="Whether the request was successful")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Complete raw response (for successful requests)")
    request_body: Optional[Dict[str, Any]] = Field(None, description="Request body data (for POST/PUT/PATCH)")
    query_parameters: Optional[Dict[str, str]] = Field(default_factory=dict, description="Query parameters used")
    response_headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Response headers")
    execution_time_ms: Optional[int] = Field(None, description="Request execution time in milliseconds")
    record_count: Optional[int] = Field(None, description="Number of records (for GET operations)")
    error_details: Optional[str] = Field(None, description="Error details (for failed requests)")
    message: Optional[str] = Field(None, description="Optional message for user information")


class MetadataRequest(BaseModel):
    """Request model for metadata retrieval"""
    
    service_name: str = Field(..., description="SAP OData service name")
    service_namespace: Optional[str] = Field(None, description="Service namespace (if different from service name)")
    odata_version: Optional[str] = Field("v4", description="OData version: v2 or v4", pattern="^(v2|v4)$")
    system_id: Optional[str] = Field(None, description="SAP system ID (e.g., 'RHA', 'RHP')")
