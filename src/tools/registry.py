"""Utility helpers for loading and instantiating SAP tools from a declarative registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import tomllib
from pydantic import Field, PrivateAttr

from ..pydantic_models.sap_tech import SAPServiceConfig
from ..utils.logger import logger
from .base_sap_tool import BaseSAPTool


@dataclass(slots=True)
class ToolDefinition:
    """Value object describing a registry-backed SAP tool."""

    name: str
    description: str
    service_config: Mapping[str, Any]
    return_direct: Optional[bool] = None
    defaults: Mapping[str, Any] = field(default_factory=dict)
    prompt_hints: List[str] = field(default_factory=list)


class RegistryBackedSAPTool(BaseSAPTool):
    """SAP tool that sources configuration and defaults from the registry."""

    prompt_hints: List[str] = Field(default_factory=list)

    _definition: ToolDefinition = PrivateAttr()
    _service_config: SAPServiceConfig = PrivateAttr()

    def __init__(self, definition: ToolDefinition):
        super().__init__(name=definition.name, description=definition.description)
        self._definition = definition
        if definition.return_direct is not None:
            self.return_direct = definition.return_direct
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
        service_details = (
            "Service details: "
            f"service_name {self._service_config.service_name}, "
            f"service_namespace {namespace}, "
            f"entity {self._service_config.entity_name}, "
            f"method {self._service_config.http_method}, "
            f"odata_version {self._service_config.odata_version}."
        )

        if base_description:
            return f"{base_description}\n\n{service_details}"
        return service_details


@lru_cache()
def _load_registry() -> Dict[str, ToolDefinition]:
    registry_path = Path(__file__).with_name("tool_registry.toml")
    if not registry_path.exists():
        logger.warning(f"Tool registry file not found at {registry_path}")
        return {}

    with registry_path.open("rb") as f:
        raw_registry = tomllib.load(f)

    tools_section = raw_registry.get("tools", {})
    definitions: Dict[str, ToolDefinition] = {}
    for tool_name, payload in tools_section.items():
        definition = ToolDefinition(
            name=tool_name,
            description=payload.get("description", ""),
            service_config=payload.get("service_config", {}),
            return_direct=payload.get("return_direct"),
            defaults=payload.get("defaults", {}),
            prompt_hints=payload.get("prompt_hints", {}).get("items", []),
        )
        definitions[tool_name] = definition
    return definitions


_TOOL_CACHE: Dict[str, RegistryBackedSAPTool] = {}


def get_registered_tool(name: str) -> RegistryBackedSAPTool:
    """Return an instantiated registry-backed tool by name."""
    if name in _TOOL_CACHE:
        return _TOOL_CACHE[name]

    definitions = _load_registry()
    definition = definitions.get(name)
    if not definition:
        raise KeyError(f"Tool '{name}' is not defined in the registry")

    tool = RegistryBackedSAPTool(definition)
    _TOOL_CACHE[name] = tool
    return tool


def get_registered_tools() -> Dict[str, RegistryBackedSAPTool]:
    """Return all registry-backed SAP tools keyed by tool name."""
    return {name: get_registered_tool(name) for name in _load_registry().keys()}


def refresh_registry() -> None:
    """Clear cached registry state so future lookups reload from disk."""
    _load_registry.cache_clear()
    _TOOL_CACHE.clear()


def render_tool_overview() -> str:
    """Generate a prompt-friendly overview of registered tools."""
    sections: List[str] = []
    for name, definition in _load_registry().items():
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
