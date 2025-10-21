"""
Dynamic tool registry storage using JSON file with versioning and hot-reload.
Can be easily replaced with database backend (PostgreSQL, MongoDB, etc.)
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import RLock
import shutil

from ..models.tool_registry_models import (
    ToolDefinitionCreate,
    ToolDefinitionUpdate,
    ToolDefinitionResponse,
    ServiceConfig,
    ToolDefaults,
    ToolPromptHints,
    ToolRegistryStats,
    ToolRegistryExport,
)
from ..utils.logger import logger


class ToolRegistryStorage:
    """
    Dynamic tool registry storage with hot-reload capability.
    
    Storage is file-based by default but can be easily replaced with database.
    Thread-safe operations with locking.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the registry storage.
        
        Args:
            storage_path: Path to JSON storage file. Defaults to data/tool_registry.json
        """
        if storage_path is None:
            # Default to data directory in project root
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(exist_ok=True)
            storage_path = str(data_dir / "tool_registry.json")
        
        self.storage_path = Path(storage_path)
        self.backup_dir = self.storage_path.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self._lock = RLock()
        self._version = 0
        self._tools: Dict[str, Dict[str, Any]] = {}
        
        # Initialize storage file if it doesn't exist
        if not self.storage_path.exists():
            self._initialize_storage()
        else:
            self._load_from_file()
        
        logger.info(f"Tool registry storage initialized: {self.storage_path}")
    
    def _initialize_storage(self):
        """Initialize empty storage file."""
        initial_data = {
            "version": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "tools": {}
        }
        self._save_to_file(initial_data)
        logger.info("Initialized empty tool registry storage")
    
    def _load_from_file(self):
        """Load registry from JSON file."""
        try:
            with self._lock:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self._version = data.get("version", 0)
                    self._tools = data.get("tools", {})
                logger.info(f"Loaded {len(self._tools)} tools from storage (version {self._version})")
        except Exception as e:
            logger.error(f"Error loading registry from file: {e}")
            raise
    
    def _save_to_file(self, data: Dict[str, Any]):
        """Save registry to JSON file with atomic write."""
        try:
            # Write to temporary file first
            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Atomic rename
            temp_path.replace(self.storage_path)
            logger.debug(f"Saved registry to file (version {data['version']})")
        except Exception as e:
            logger.error(f"Error saving registry to file: {e}")
            raise
    
    def _create_backup(self):
        """Create a backup of current registry."""
        if not self.storage_path.exists():
            return
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"tool_registry_v{self._version}_{timestamp}.json"
        
        try:
            shutil.copy2(self.storage_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            
            # Keep only last 10 backups
            self._cleanup_old_backups(keep=10)
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
    
    def _cleanup_old_backups(self, keep: int = 10):
        """Remove old backup files, keeping only the most recent ones."""
        try:
            backups = sorted(
                self.backup_dir.glob("tool_registry_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            for backup in backups[keep:]:
                backup.unlink()
                logger.debug(f"Removed old backup: {backup}")
        except Exception as e:
            logger.warning(f"Error cleaning up backups: {e}")
    
    def create_tool(self, tool_data: ToolDefinitionCreate) -> ToolDefinitionResponse:
        """
        Create a new tool definition.
        
        Args:
            tool_data: Tool definition to create
            
        Returns:
            Created tool definition
            
        Raises:
            ValueError: If tool with same name already exists
        """
        with self._lock:
            if tool_data.name in self._tools:
                raise ValueError(f"Tool '{tool_data.name}' already exists")
            
            # Create backup before modification
            self._create_backup()
            
            now = datetime.utcnow()
            tool_dict = {
                "name": tool_data.name,
                "description": tool_data.description,
                "service_config": tool_data.service_config.dict(),
                "return_direct": tool_data.return_direct,
                "defaults": tool_data.defaults.dict() if tool_data.defaults else {},
                "prompt_hints": tool_data.prompt_hints.dict() if tool_data.prompt_hints else {"items": []},
                "enabled": tool_data.enabled,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "version": 1
            }
            
            self._tools[tool_data.name] = tool_dict
            self._version += 1
            
            # Save to file
            self._save_to_file({
                "version": self._version,
                "created_at": self._tools.get(list(self._tools.keys())[0], {}).get("created_at", now.isoformat()) if self._tools else now.isoformat(),
                "updated_at": now.isoformat(),
                "tools": self._tools
            })
            
            logger.info(f"Created tool: {tool_data.name}")
            return self._tool_dict_to_response(tool_dict)
    
    def get_tool(self, tool_name: str) -> Optional[ToolDefinitionResponse]:
        """
        Get a tool definition by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool definition or None if not found
        """
        with self._lock:
            tool_dict = self._tools.get(tool_name)
            if tool_dict:
                return self._tool_dict_to_response(tool_dict)
            return None
    
    def list_tools(self, enabled_only: bool = False) -> List[ToolDefinitionResponse]:
        """
        List all tool definitions.
        
        Args:
            enabled_only: If True, return only enabled tools
            
        Returns:
            List of tool definitions
        """
        with self._lock:
            tools = [
                self._tool_dict_to_response(tool)
                for tool in self._tools.values()
                if not enabled_only or tool.get("enabled", True)
            ]
            return sorted(tools, key=lambda t: t.name)
    
    def update_tool(self, tool_name: str, updates: ToolDefinitionUpdate) -> ToolDefinitionResponse:
        """
        Update an existing tool definition.
        
        Args:
            tool_name: Name of the tool to update
            updates: Fields to update
            
        Returns:
            Updated tool definition
            
        Raises:
            ValueError: If tool not found
        """
        with self._lock:
            if tool_name not in self._tools:
                raise ValueError(f"Tool '{tool_name}' not found")
            
            # Create backup before modification
            self._create_backup()
            
            tool_dict = self._tools[tool_name]
            
            # Update fields
            if updates.description is not None:
                tool_dict["description"] = updates.description
            if updates.service_config is not None:
                tool_dict["service_config"] = updates.service_config.dict()
            if updates.return_direct is not None:
                tool_dict["return_direct"] = updates.return_direct
            if updates.defaults is not None:
                tool_dict["defaults"] = updates.defaults.dict()
            if updates.prompt_hints is not None:
                tool_dict["prompt_hints"] = updates.prompt_hints.dict()
            if updates.enabled is not None:
                tool_dict["enabled"] = updates.enabled
            
            # Update metadata
            now = datetime.utcnow()
            tool_dict["updated_at"] = now.isoformat()
            tool_dict["version"] = tool_dict.get("version", 1) + 1
            
            self._version += 1
            
            # Save to file
            self._save_to_file({
                "version": self._version,
                "created_at": list(self._tools.values())[0].get("created_at", now.isoformat()) if self._tools else now.isoformat(),
                "updated_at": now.isoformat(),
                "tools": self._tools
            })
            
            logger.info(f"Updated tool: {tool_name}")
            return self._tool_dict_to_response(tool_dict)
    
    def delete_tool(self, tool_name: str) -> bool:
        """
        Delete a tool definition.
        
        Args:
            tool_name: Name of the tool to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if tool_name not in self._tools:
                return False
            
            # Create backup before modification
            self._create_backup()
            
            del self._tools[tool_name]
            self._version += 1
            
            now = datetime.utcnow()
            # Save to file
            self._save_to_file({
                "version": self._version,
                "created_at": list(self._tools.values())[0].get("created_at", now.isoformat()) if self._tools else now.isoformat(),
                "updated_at": now.isoformat(),
                "tools": self._tools
            })
            
            logger.info(f"Deleted tool: {tool_name}")
            return True
    
    def get_stats(self) -> ToolRegistryStats:
        """Get statistics about the tool registry."""
        with self._lock:
            enabled = sum(1 for t in self._tools.values() if t.get("enabled", True))
            return ToolRegistryStats(
                total_tools=len(self._tools),
                enabled_tools=enabled,
                disabled_tools=len(self._tools) - enabled,
                last_updated=datetime.fromisoformat(
                    max([t.get("updated_at", t.get("created_at", datetime.utcnow().isoformat())) 
                         for t in self._tools.values()] + [datetime.utcnow().isoformat()])
                ),
                registry_version=self._version
            )
    
    def export_registry(self) -> ToolRegistryExport:
        """Export the entire registry."""
        with self._lock:
            tools = {
                name: self._tool_dict_to_response(tool)
                for name, tool in self._tools.items()
            }
            return ToolRegistryExport(
                version=self._version,
                exported_at=datetime.utcnow(),
                tools=tools
            )
    
    def import_registry(self, tools: Dict[str, ToolDefinitionCreate], replace_existing: bool = False):
        """
        Import tools into the registry.
        
        Args:
            tools: Dictionary of tool definitions to import
            replace_existing: If True, replace existing tools with same name
        """
        with self._lock:
            # Create backup before bulk modification
            self._create_backup()
            
            imported = 0
            skipped = 0
            
            for name, tool_data in tools.items():
                if name in self._tools and not replace_existing:
                    skipped += 1
                    logger.debug(f"Skipped existing tool: {name}")
                    continue
                
                now = datetime.utcnow()
                tool_dict = {
                    "name": name,
                    "description": tool_data.description,
                    "service_config": tool_data.service_config.dict(),
                    "return_direct": tool_data.return_direct,
                    "defaults": tool_data.defaults.dict() if tool_data.defaults else {},
                    "prompt_hints": tool_data.prompt_hints.dict() if tool_data.prompt_hints else {"items": []},
                    "enabled": tool_data.enabled,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "version": 1
                }
                
                self._tools[name] = tool_dict
                imported += 1
            
            self._version += 1
            
            # Save to file
            now = datetime.utcnow()
            self._save_to_file({
                "version": self._version,
                "created_at": list(self._tools.values())[0].get("created_at", now.isoformat()) if self._tools else now.isoformat(),
                "updated_at": now.isoformat(),
                "tools": self._tools
            })
            
            logger.info(f"Imported {imported} tools, skipped {skipped}")
    
    def reload(self):
        """Reload registry from file (hot-reload)."""
        logger.info("Reloading tool registry from storage...")
        self._load_from_file()
    
    def _tool_dict_to_response(self, tool_dict: Dict[str, Any]) -> ToolDefinitionResponse:
        """Convert internal dict representation to response model."""
        return ToolDefinitionResponse(
            name=tool_dict["name"],
            description=tool_dict["description"],
            service_config=ServiceConfig(**tool_dict["service_config"]),
            return_direct=tool_dict.get("return_direct"),
            defaults=ToolDefaults(**tool_dict.get("defaults", {})),
            prompt_hints=ToolPromptHints(**tool_dict.get("prompt_hints", {"items": []})),
            enabled=tool_dict.get("enabled", True),
            created_at=datetime.fromisoformat(tool_dict["created_at"]),
            updated_at=datetime.fromisoformat(tool_dict["updated_at"]),
            version=tool_dict.get("version", 1)
        )


# Singleton instance
_storage_instance: Optional[ToolRegistryStorage] = None


def get_tool_registry_storage() -> ToolRegistryStorage:
    """Get or create the singleton tool registry storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = ToolRegistryStorage()
    return _storage_instance
