"""
Pydantic models for dynamic tool registry management.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class ServiceConfig(BaseModel):
    """Service configuration for a tool."""
    service_name: str = Field(..., description="SAP OData service name")
    service_namespace: Optional[str] = Field(None, description="Service namespace for OData v4")
    entity_name: str = Field(..., description="Entity name or endpoint path")
    odata_version: str = Field(default="v4", pattern="^(v2|v4)$")
    http_method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH|DELETE)$")


class ToolDefaults(BaseModel):
    """Default parameters for a tool."""
    query_parameters: Optional[Dict[str, str]] = Field(default_factory=dict)
    request_body: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ToolPromptHints(BaseModel):
    """Prompt hints for a tool."""
    items: List[str] = Field(default_factory=list, description="List of usage hints")


class ToolDefinitionCreate(BaseModel):
    """Model for creating a new tool definition."""
    name: str = Field(..., min_length=1, max_length=100, description="Unique tool name")
    description: str = Field(..., min_length=1, description="Tool description")
    service_config: ServiceConfig
    return_direct: Optional[bool] = Field(None, description="Whether tool returns directly")
    defaults: Optional[ToolDefaults] = Field(default_factory=ToolDefaults)
    prompt_hints: Optional[ToolPromptHints] = Field(default_factory=ToolPromptHints)
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    
    @field_validator('name')
    def validate_name(cls, v):
        """Validate tool name format."""
        if not v.replace('_', '').isalnum():
            raise ValueError('Tool name must be alphanumeric with underscores')
        return v


class ToolDefinitionUpdate(BaseModel):
    """Model for updating an existing tool definition."""
    description: Optional[str] = Field(None, min_length=1)
    service_config: Optional[ServiceConfig] = Field(None)
    return_direct: Optional[bool] = Field(None)
    defaults: Optional[ToolDefaults] = Field(None)
    prompt_hints: Optional[ToolPromptHints] = Field(None)
    enabled: Optional[bool] = Field(None)
    
    class Config:
        """Allow updates with only some fields."""
        extra = "forbid"


class ToolDefinitionResponse(BaseModel):
    """Model for tool definition response."""
    name: str
    description: str
    service_config: ServiceConfig
    return_direct: Optional[bool]
    defaults: ToolDefaults
    prompt_hints: ToolPromptHints
    enabled: bool
    created_at: datetime
    updated_at: datetime
    version: int


class ToolRegistryStats(BaseModel):
    """Statistics about the tool registry."""
    total_tools: int
    enabled_tools: int
    disabled_tools: int
    last_updated: datetime
    registry_version: int


class ToolRegistryExport(BaseModel):
    """Export format for tool registry."""
    version: int
    exported_at: datetime
    tools: Dict[str, ToolDefinitionResponse]


class ToolRegistryImport(BaseModel):
    """Import format for tool registry."""
    tools: Dict[str, ToolDefinitionCreate]
    replace_existing: bool = Field(default=False, description="Whether to replace existing tools")
