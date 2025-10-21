"""
Admin API router for dynamic tool registry management.
Provides CRUD operations for tool definitions with hot-reload capability.
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional

from ..models.tool_registry_models import (
    ToolDefinitionCreate,
    ToolDefinitionUpdate,
    ToolDefinitionResponse,
    ToolRegistryStats,
    ToolRegistryExport,
    ToolRegistryImport,
)
from ..services.tool_registry_storage import get_tool_registry_storage
from ..tools import refresh_tool_registry
from ..utils.logger import logger

router = APIRouter()


@router.post(
    "/tools",
    response_model=ToolDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Tool",
    description="Create a new tool definition in the registry. Changes are immediately available without server restart.",
)
async def create_tool(tool: ToolDefinitionCreate) -> ToolDefinitionResponse:
    """
    Create a new tool definition.
    
    The tool will be immediately available for use without requiring a server restart.
    """
    try:
        storage = get_tool_registry_storage()
        result = storage.create_tool(tool)
        
        # Trigger hot-reload of tools
        refresh_tool_registry()
        
        logger.info(f"Admin: Created tool '{tool.name}'")
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating tool: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/tools",
    response_model=List[ToolDefinitionResponse],
    summary="List All Tools",
    description="Get a list of all tool definitions in the registry.",
)
async def list_tools(
    enabled_only: bool = Query(False, description="Return only enabled tools")
) -> List[ToolDefinitionResponse]:
    """
    List all tool definitions.
    
    Args:
        enabled_only: If true, return only enabled tools
    """
    try:
        storage = get_tool_registry_storage()
        return storage.list_tools(enabled_only=enabled_only)
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/tools/{tool_name}",
    response_model=ToolDefinitionResponse,
    summary="Get Tool Details",
    description="Get detailed information about a specific tool.",
)
async def get_tool(tool_name: str) -> ToolDefinitionResponse:
    """
    Get a specific tool definition by name.
    
    Args:
        tool_name: Name of the tool to retrieve
    """
    try:
        storage = get_tool_registry_storage()
        tool = storage.get_tool(tool_name)
        
        if tool is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool '{tool_name}' not found"
            )
        
        return tool
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put(
    "/tools/{tool_name}",
    response_model=ToolDefinitionResponse,
    summary="Update Tool",
    description="Update an existing tool definition. Changes are immediately available without server restart.",
)
async def update_tool(tool_name: str, updates: ToolDefinitionUpdate) -> ToolDefinitionResponse:
    """
    Update an existing tool definition.
    
    Only provided fields will be updated. The tool will be immediately available with updates.
    
    Args:
        tool_name: Name of the tool to update
        updates: Fields to update
    """
    try:
        storage = get_tool_registry_storage()
        result = storage.update_tool(tool_name, updates)
        
        # Trigger hot-reload of tools
        refresh_tool_registry()
        
        logger.info(f"Admin: Updated tool '{tool_name}'")
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating tool: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/tools/{tool_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Tool",
    description="Delete a tool definition from the registry. Changes are immediately effective.",
)
async def delete_tool(tool_name: str):
    """
    Delete a tool definition.
    
    The tool will be immediately removed and no longer available.
    
    Args:
        tool_name: Name of the tool to delete
    """
    try:
        storage = get_tool_registry_storage()
        deleted = storage.delete_tool(tool_name)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool '{tool_name}' not found"
            )
        
        # Trigger hot-reload of tools
        refresh_tool_registry()
        
        logger.info(f"Admin: Deleted tool '{tool_name}'")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tool: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/stats",
    response_model=ToolRegistryStats,
    summary="Get Registry Statistics",
    description="Get statistics about the tool registry.",
)
async def get_stats() -> ToolRegistryStats:
    """Get statistics about the tool registry."""
    try:
        storage = get_tool_registry_storage()
        return storage.get_stats()
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/reload",
    summary="Reload Registry",
    description="Reload the tool registry from storage (hot-reload without server restart).",
)
async def reload_registry():
    """
    Reload the tool registry from storage.
    
    This will refresh all tool definitions from the storage without requiring a server restart.
    """
    try:
        storage = get_tool_registry_storage()
        storage.reload()
        refresh_tool_registry()
        
        stats = storage.get_stats()
        
        logger.info("Admin: Registry reloaded")
        return {
            "success": True,
            "message": "Registry reloaded successfully",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error reloading registry: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/export",
    response_model=ToolRegistryExport,
    summary="Export Registry",
    description="Export the entire tool registry for backup or migration.",
)
async def export_registry() -> ToolRegistryExport:
    """
    Export the entire tool registry.
    
    This can be used for backup, version control, or migrating to another instance.
    """
    try:
        storage = get_tool_registry_storage()
        return storage.export_registry()
    except Exception as e:
        logger.error(f"Error exporting registry: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/import",
    summary="Import Registry",
    description="Import tool definitions into the registry from a backup or export.",
)
async def import_registry(import_data: ToolRegistryImport):
    """
    Import tool definitions into the registry.
    
    Args:
        import_data: Tool definitions to import and whether to replace existing tools
    """
    try:
        storage = get_tool_registry_storage()
        storage.import_registry(
            tools=import_data.tools,
            replace_existing=import_data.replace_existing
        )
        
        # Trigger hot-reload of tools
        refresh_tool_registry()
        
        stats = storage.get_stats()
        
        logger.info(f"Admin: Imported tools (replace_existing={import_data.replace_existing})")
        return {
            "success": True,
            "message": "Tools imported successfully",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error importing registry: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/tools/{tool_name}/enable",
    response_model=ToolDefinitionResponse,
    summary="Enable Tool",
    description="Enable a disabled tool.",
)
async def enable_tool(tool_name: str) -> ToolDefinitionResponse:
    """
    Enable a tool that was previously disabled.
    
    Args:
        tool_name: Name of the tool to enable
    """
    try:
        storage = get_tool_registry_storage()
        result = storage.update_tool(tool_name, ToolDefinitionUpdate(enabled=True))  # type: ignore
        
        # Trigger hot-reload of tools
        refresh_tool_registry()
        
        logger.info(f"Admin: Enabled tool '{tool_name}'")
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error enabling tool: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/tools/{tool_name}/disable",
    response_model=ToolDefinitionResponse,
    summary="Disable Tool",
    description="Disable a tool without deleting it.",
)
async def disable_tool(tool_name: str) -> ToolDefinitionResponse:
    """
    Disable a tool without deleting it.
    
    Disabled tools will not be available to the agent but can be re-enabled later.
    
    Args:
        tool_name: Name of the tool to disable
    """
    try:
        storage = get_tool_registry_storage()
        result = storage.update_tool(tool_name, ToolDefinitionUpdate(enabled=False))  # type: ignore
        
        # Trigger hot-reload of tools
        refresh_tool_registry()
        
        logger.info(f"Admin: Disabled tool '{tool_name}'")
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error disabling tool: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
