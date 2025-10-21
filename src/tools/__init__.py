"""SAP tools package with registry-backed auto-discovery."""

from __future__ import annotations

from typing import Dict, List

from .dynamic_registry import (
	RegistryBackedSAPTool,
	get_registered_tool,
	get_registered_tools,
	refresh_registry,
	render_tool_overview,
)

REGISTERED_SAP_TOOLS: Dict[str, RegistryBackedSAPTool] = get_registered_tools()
__all__: List[str] = []


def list_sap_tools() -> List[RegistryBackedSAPTool]:
	"""Return the list of all registry-backed SAP tools."""
	return list(REGISTERED_SAP_TOOLS.values())


def refresh_tool_registry() -> None:
	"""Reload tool definitions from the TOML registry."""
	global REGISTERED_SAP_TOOLS
	refresh_registry()
	REGISTERED_SAP_TOOLS = get_registered_tools()
	_update_exports()


def _build_exports() -> List[str]:
	base_exports = [
		"REGISTERED_SAP_TOOLS",
		"RegistryBackedSAPTool",
		"get_registered_tool",
		"get_registered_tools",
		"list_sap_tools",
		"refresh_tool_registry",
		"render_tool_overview",
	]
	return base_exports + sorted(get_registered_tools().keys())


def _update_exports() -> None:
	global __all__
	__all__ = _build_exports()


def __getattr__(name: str) -> RegistryBackedSAPTool:
	try:
		tool = get_registered_tool(name)
	except KeyError as exc:  # pragma: no cover - attribute fallback
		raise AttributeError(f"module 'src.tools' has no attribute '{name}'") from exc
	REGISTERED_SAP_TOOLS[name] = tool
	return tool


def __dir__() -> List[str]:  # pragma: no cover - convenience
	exported = set(globals().keys()) | set(get_registered_tools().keys())
	return sorted(exported)


_update_exports()