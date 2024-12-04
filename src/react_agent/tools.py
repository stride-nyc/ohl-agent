"""This module provides tools for the ReAct Agent using MCP servers.

Tools are dynamically loaded from configured MCP servers at startup.
"""

from typing import Any, Callable, List, Optional
import asyncio

from react_agent.configuration import Configuration
from react_agent.mcp_client import MCPClientManager


# Global MCP client manager
_mcp_manager: Optional[MCPClientManager] = None


async def initialize_tools(config: Configuration) -> List[Callable[..., Any]]:
    """Initialize MCP servers and return available tools.
    
    This should be called during application startup.
    """
    global _mcp_manager
    
    _mcp_manager = MCPClientManager()
    await _mcp_manager.start_all_servers(config)
    
    return _mcp_manager.get_all_tools()


async def cleanup_tools() -> None:
    """Cleanup MCP servers and tools.
    
    This should be called during application shutdown.
    """
    global _mcp_manager
    if _mcp_manager:
        await _mcp_manager.shutdown()
        _mcp_manager = None


# Initial empty tools list - will be populated during startup
TOOLS: List[Callable[..., Any]] = []
