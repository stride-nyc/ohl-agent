"""This module provides tools for the ReAct Agent using MCP servers.

Tools are dynamically loaded from MCP servers through the gateway.
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import BaseTool, Tool

from react_agent import mcp_client

logger = logging.getLogger(__name__)


def _create_tool_wrapper(tool_def: Dict[str, Any]) -> Callable[..., Any]:
    """Create a wrapper function for an MCP tool.
    
    Args:
        tool_def: Tool definition from the MCP server
        
    Returns:
        A function that wraps the tool
    """
    logger.info(f"Creating wrapper for tool: {tool_def['name']}")
    if "input_schema" in tool_def:
        logger.info(f"Tool {tool_def['name']} input schema: {tool_def['input_schema']}")
    
    async def wrapper(*args, **kwargs) -> Any:
        """Wrapper function that calls the MCP tool."""
        # Log everything about this call
        logger.info(f"Tool {tool_def['name']} called with:")
        logger.info(f"  args: {args}")
        logger.info(f"  kwargs: {kwargs}")
        logger.info(f"  wrapper signature: {inspect.signature(wrapper)}")
        
        # If we have args, convert first arg to kwargs
        if args and len(args) > 0:
            logger.info(f"Converting args[0] to kwargs: {args[0]}")
            if isinstance(args[0], str):
                try:
                    import json
                    kwargs = json.loads(args[0])
                    logger.info(f"Parsed JSON string to kwargs: {kwargs}")
                except json.JSONDecodeError:
                    kwargs = {"path": args[0]}
                    logger.info(f"Using string as path: {kwargs}")
            elif isinstance(args[0], dict):
                kwargs = args[0]
                logger.info(f"Using dict as kwargs: {kwargs}")
        
        logger.info(f"Calling mcp_client with kwargs: {kwargs}")
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
                logger.info(f"Adding parameter {name} to {tool_def['name']}")
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
            logger.info(f"Created signature for {tool_def['name']}: {wrapper.__signature__}")
    
    return wrapper


def _load_tools() -> List[BaseTool]:
    """Load all available tools from the MCP gateway.
    
    Returns:
        List of tool functions wrapped as LangChain tools
    """
    logger.info("Loading tools from gateway")
    tools = []
    for tool_def in mcp_client.list_tools():
        logger.info(f"Creating tool for: {tool_def['name']}")
        wrapper = _create_tool_wrapper(tool_def)
        tool = Tool(
            name=tool_def["name"],
            description=tool_def.get("description", ""),
            func=wrapper,
            coroutine=wrapper,
        )
        logger.info(f"Created tool: {tool}")
        tools.append(tool)
    return tools


# Initial empty tools list - will be populated during startup
TOOLS: List[BaseTool] = []


async def initialize_tools(config) -> List[BaseTool]:
    """Initialize connection to MCP gateway and get available tools.
    
    This should be called during application startup.
    
    Args:
        config: Application configuration
        
    Returns:
        List of available tools
    """
    global TOOLS
    
    logger.info("Initializing tools")
    
    # Configure MCP client with gateway URL from config
    if hasattr(config, "mcp_gateway_url"):
        mcp_client.get_client(config.mcp_gateway_url)
    
    # Load tools from gateway
    TOOLS = _load_tools()
    
    logger.info(f"Initialized {len(TOOLS)} tools")
    return TOOLS
