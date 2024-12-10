"""This module provides tools for the ReAct Agent using MCP servers.

Tools are dynamically loaded from MCP servers through the gateway.
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional

from react_agent import mcp_client


def _create_tool_wrapper(tool_def: Dict[str, Any]) -> Callable[..., Any]:
    """Create a wrapper function for an MCP tool.
    
    Args:
        tool_def: Tool definition from the MCP server
        
    Returns:
        A function that wraps the tool
    """
    async def wrapper(**kwargs) -> Any:
        """Wrapper function that calls the MCP tool."""
        return mcp_client.call_tool(tool_def["name"], kwargs)
        
    # Set metadata on wrapper function
    wrapper.__name__ = tool_def["name"]
    wrapper.__doc__ = tool_def.get("description", "")
    
    # Set signature based on input schema if available
    if "input_schema" in tool_def:
        schema = tool_def["input_schema"]
        if isinstance(schema, dict) and "properties" in schema:
            params = []
            required = schema.get("required", [])
            for name, prop in schema["properties"].items():
                annotation = Any  # Could map JSON schema types to Python types
                default = ... if name in required else None
                params.append(
                    inspect.Parameter(
                        name=name,
                        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        default=default,
                        annotation=annotation
                    )
                )
            wrapper.__signature__ = inspect.Signature(params)
    
    return wrapper


def _load_tools() -> List[Callable[..., Any]]:
    """Load all available tools from the MCP gateway.
    
    Returns:
        List of tool functions
    """
    tools = []
    for tool_def in mcp_client.list_tools():
        wrapper = _create_tool_wrapper(tool_def)
        tools.append(wrapper)
    return tools


# Initial empty tools list - will be populated during startup
TOOLS: List[Callable[..., Any]] = []


async def initialize_tools(config) -> List[Callable[..., Any]]:
    """Initialize connection to MCP gateway and get available tools.
    
    This should be called during application startup.
    
    Args:
        config: Application configuration
        
    Returns:
        List of available tools
    """
    global TOOLS
    
    # Configure MCP client with gateway URL from config
    if hasattr(config, "mcp_gateway_url"):
        mcp_client.get_client(config.mcp_gateway_url)
    
    # Load tools from gateway
    TOOLS = _load_tools()
    
    return TOOLS
