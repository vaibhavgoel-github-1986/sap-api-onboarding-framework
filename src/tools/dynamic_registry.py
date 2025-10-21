"""
Dynamic tool registry that loads from JSON storage instead of TOML.
Maintains backward compatibility with the TOML-based system.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Mapping, Optional

from pydantic import Field, PrivateAttr

from ..pydantic_models.sap_tech import SAPServiceConfig
from ..utils.logger import logger
from .base_sap_tool import BaseSAPTool
from ..services.tool_registry_storage import get_tool_registry_storage


@dataclass(slots=True)
class ToolDefinition:
    """Value object describing a registry-backed SAP tool."""

    name: str
    description: str
    service_config: Mapping[str, Any]
    return_direct: Optional[bool] = None
    defaults: Mapping[str, Any] = field(default_factory=dict)
    prompt_hints: List[str] = field(default_factory=list)
    enabled: bool = True


class RegistryBackedSAPTool(BaseSAPTool):
    """SAP tool that sources configuration and defaults from the dynamic registry."""

    prompt_hints: List[str] = Field(default_factory=list)

    _definition: ToolDefinition = PrivateAttr()
    _service_config: SAPServiceConfig = PrivateAttr()

    def __init__(self, definition: ToolDefinition):
        super().__init__(name=definition.name, description=definition.description)
        self._definition = definition
        # Use definition's return_direct if specified, otherwise use False (return to LLM)
        # When return_direct=False, the API response goes back to the LLM for processing
        # When return_direct=True, the response is returned directly to the user
        self.return_direct = definition.return_direct if definition.return_direct is not None else False
        self.prompt_hints = list(definition.prompt_hints)
        self._service_config = SAPServiceConfig(**definition.service_config)
        self.description = self._build_description(definition.description)

    def get_service_config(self, **kwargs: Any) -> SAPServiceConfig:
        return self._service_config

    def populate_request_params(self, **kwargs: Any) -> Dict[str, Any]:
        params = super().populate_request_params(**kwargs)
        params.setdefault("service_name", self._service_config.service_name)
        if self._service_config.service_namespace:
            params.setdefault("service_namespace", self._service_config.service_namespace)
        params.setdefault("entity_name", self._service_config.entity_name)
        params.setdefault("odata_version", self._service_config.odata_version)
        params.setdefault("http_method", self._service_config.http_method)

        defaults = self._definition.defaults
        if defaults:
            query_defaults = defaults.get("query_parameters")
            if query_defaults and not params.get("query_parameters"):
                params["query_parameters"] = query_defaults

            request_defaults = defaults.get("request_body")
            if request_defaults and not params.get("request_body"):
                params["request_body"] = request_defaults

        return params

    def _build_description(self, raw_description: str) -> str:
        base_description = (raw_description or "").strip()
        namespace = self._service_config.service_namespace or "n/a"
        
        # Build clear, prominently displayed service details
        service_details = (
            "\n\n"
            "═══════════════════════════════════════════════════════\n"
            "� SERVICE CONFIGURATION (Use these for get_metadata first):\n"
            "═══════════════════════════════════════════════════════\n"
            f"service_name: {self._service_config.service_name}\n"
            f"service_namespace: {namespace}\n"
            f"entity_name: {self._service_config.entity_name}\n"
            f"http_method: {self._service_config.http_method}\n"
            f"odata_version: {self._service_config.odata_version}\n"
            "═══════════════════════════════════════════════════════\n"
            "\n"
            "🔄 WORKFLOW:\n"
            "1. Call get_metadata with the service details above (plus system_id)\n"
            "2. Analyze the metadata response\n"
            "3. Call this tool with system_id and query_parameters (service details auto-filled)\n"
        )

        if base_description:
            return f"{base_description}{service_details}"
        return service_details.strip()


def _load_registry_from_storage() -> Dict[str, ToolDefinition]:
    """Load tool definitions from JSON storage instead of TOML."""
    storage = get_tool_registry_storage()
    
    # Load only enabled tools
    tools = storage.list_tools(enabled_only=True)
    
    definitions: Dict[str, ToolDefinition] = {}
    for tool in tools:
        definition = ToolDefinition(
            name=tool.name,
            description=tool.description,
            service_config=tool.service_config.dict(),
            return_direct=tool.return_direct,
            defaults=tool.defaults.dict(),
            prompt_hints=tool.prompt_hints.items if tool.prompt_hints else [],
            enabled=tool.enabled,
        )
        definitions[tool.name] = definition
    
    logger.info(f"Loaded {len(definitions)} enabled tools from dynamic registry")
    return definitions


# Cache for tool instances
_TOOL_CACHE: Dict[str, RegistryBackedSAPTool] = {}


def get_registered_tool(name: str) -> RegistryBackedSAPTool:
    """Return an instantiated registry-backed tool by name."""
    if name in _TOOL_CACHE:
        return _TOOL_CACHE[name]

    definitions = _load_registry_from_storage()
    definition = definitions.get(name)
    if not definition:
        raise KeyError(f"Tool '{name}' is not defined in the registry")

    tool = RegistryBackedSAPTool(definition)
    _TOOL_CACHE[name] = tool
    return tool


def get_registered_tools() -> Dict[str, RegistryBackedSAPTool]:
    """Return all registry-backed SAP tools keyed by tool name."""
    definitions = _load_registry_from_storage()
    tools = {}
    for name, definition in definitions.items():
        if name in _TOOL_CACHE:
            tools[name] = _TOOL_CACHE[name]
        else:
            tool = RegistryBackedSAPTool(definition)
            _TOOL_CACHE[name] = tool
            tools[name] = tool
    return tools


def refresh_registry() -> None:
    """Clear cached registry state so future lookups reload from storage."""
    _TOOL_CACHE.clear()
    logger.info("Tool registry cache cleared - will reload from storage on next access")


def render_tool_overview() -> str:
    """Generate a prompt-friendly overview of registered tools."""
    definitions = _load_registry_from_storage()
    sections: List[str] = []
    
    for name, definition in definitions.items():
        hints = definition.prompt_hints
        hint_lines = "".join(f"  - {hint}\n" for hint in hints) if hints else ""
        section = (
            f"### {name}\n"
            f"{definition.description.strip()}\n"
            "\n"
            f"Default Service Configuration:\n"
            f"  - Service: {definition.service_config.get('service_name')}\n"
            f"  - Namespace: {definition.service_config.get('service_namespace', 'n/a')}\n"
            f"  - Entity: {definition.service_config.get('entity_name')}\n"
            f"  - Method: {definition.service_config.get('http_method', 'GET')}\n"
        )
        if hint_lines:
            section += "\nUsage Tips:\n" + hint_lines
        sections.append(section.rstrip())
    
    return "\n\n".join(sections)
