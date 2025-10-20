"""This module provides tools for the ReAct Agent using MCP servers.

Tools are dynamically loaded from MCP servers through the gateway.
"""

import asyncio
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Literal, Optional, Set, Type, Annotated

from langchain_core.tools import BaseTool, Tool, StructuredTool, tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from pydantic import BaseModel, create_model

from react_agent import mcp_client

logger = logging.getLogger(__name__)


def get_schema(tool_def: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get the input schema from a tool definition, handling both naming conventions."""
    # Try both input_schema and inputSchema
    schema = tool_def.get("input_schema") or tool_def.get("inputSchema")
    if schema:
        logger.info(f"Found schema for tool {tool_def['name']}: {json.dumps(schema, indent=2)}")
    else:
        logger.info(f"No schema found for tool {tool_def['name']}")
    return schema


def create_schema_model(tool_def: Dict[str, Any]) -> Optional[Type[BaseModel]]:
    """Create a Pydantic model from the tool's schema."""
    schema = get_schema(tool_def)
    if not schema or not isinstance(schema, dict):
        return None
        
    properties = schema.get("properties", {})
    if not properties:
        return None
        
    # Convert JSON schema types to Python types
    field_definitions = {}
    for name, prop in properties.items():
        logger.info(f"Adding field {name} to schema model for {tool_def['name']}")
        python_type = str if prop.get("type") == "string" else Any
        required = name in schema.get("required", [])
        field_definitions[name] = (python_type, ... if required else None)
    
    # Create the model
    model = create_model(
        f"{tool_def['name']}Args",
        **field_definitions
    )
    logger.info(f"Created schema model for {tool_def['name']}: {model}")
    return model


def _create_tool_wrapper(tool_def: Dict[str, Any]) -> BaseTool:
    """Create a wrapper function for an MCP tool.
    
    Args:
        tool_def: Tool definition from the MCP server
        
    Returns:
        A LangChain Tool
    """
    async def wrapper(*args, **kwargs) -> Any:
        """Wrapper function that calls the MCP tool."""
        # Convert args to kwargs if needed
        if args:
            logger.info(f"Converting args to kwargs: {args}")
            if len(args) == 1 and isinstance(args[0], str):
                # If we get a single string argument, treat it as the first schema property
                schema = get_schema(tool_def)
                if schema and schema.get("properties"):
                    first_prop = next(iter(schema["properties"]))
                    kwargs[first_prop] = args[0]
                    logger.info(f"Converted string arg to {first_prop}: {args[0]}")
            elif len(args) == 1 and isinstance(args[0], dict):
                # If we get a dict argument, merge it with kwargs
                kwargs.update(args[0])
                logger.info(f"Merged dict arg with kwargs: {args[0]}")
        
        logger.info(f"Tool wrapper calling with kwargs: {kwargs}")
        result = await mcp_client.call_tool(tool_def["name"], kwargs)
        return result
    
    # Create Pydantic model for schema validation
    args_schema = create_schema_model(tool_def)
    
    # Check if we need a structured tool (multiple parameters) or simple tool
    schema = get_schema(tool_def)
    if schema and len(schema.get("properties", {})) > 1:
        # Use StructuredTool for multiple parameters
        tool = StructuredTool(
            name=tool_def["name"],
            description=tool_def.get("description", ""),
            func=wrapper,
            coroutine=wrapper,
            args_schema=args_schema
        )
    else:
        # Use regular Tool for single or no parameters
        tool = Tool(
            name=tool_def["name"],
            description=tool_def.get("description", ""),
            func=wrapper,
            coroutine=wrapper,
            args_schema=args_schema
        )
    
    logger.info(f"Created tool: {tool}")
    return tool


# State management tools

@tool
def get_conversation_history(
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[Dict, InjectedState]
) -> Command[Literal["call_model"]]:
    """Get the current conversation history between member and automated system.
    
    Returns the conversation formatted for review.
    """
    history = state.get("conversation_history", [])
    
    if not history:
        content = "No conversation history available."
    else:
        formatted = []
        for msg in history:
            role = msg.get("role", "unknown").upper()
            content_text = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            time_str = f" [{timestamp}]" if timestamp else ""
            formatted.append(f"{role}{time_str}: {content_text}")
        content = "\n\n".join(formatted)
    
    return Command(
        update={
            "messages": [ToolMessage(
                content=f"Conversation History:\n\n{content}",
                tool_call_id=tool_call_id
            )]
        }
    )


@tool
def get_escalation_context(
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[Dict, InjectedState]
) -> Command[Literal["call_model"]]:
    """Get the escalation context including reason, urgency, and member sentiment.
    
    Returns information about why this conversation was escalated.
    """
    context = state.get("escalation_context")
    
    if not context:
        content = "No escalation context available."
    else:
        content = f"""Escalation Context:
- Reason: {context.get('reason', 'Not specified')}
- Urgency: {context.get('urgency', 'Not specified')}
- Member Sentiment: {context.get('member_sentiment', 'Not specified')}"""
    
    return Command(
        update={
            "messages": [ToolMessage(
                content=content,
                tool_call_id=tool_call_id
            )]
        }
    )


@tool
def set_proposed_response(
    message: str,
    reasoning: str,
    suggested_tone: str,
    relevant_docs: Optional[str] = None,
    key_points: Optional[str] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
    state: Annotated[Dict, InjectedState] = None
) -> Command[Literal["call_model"]]:
    """Set the proposed response that the human agent should send to the member.
    
    Args:
        message: The exact text the agent should send to the member
        reasoning: Explanation of why this approach was chosen
        suggested_tone: The tone to use (e.g., 'empathetic', 'professional', 'apologetic')
        relevant_docs: Comma-separated list of documentation references (e.g., 'samples.md#apologies, faq.md#pharmacy')
        key_points: Comma-separated list of key points to cover
    
    Returns:
        Confirmation of the proposed response being set
    """
    # Parse comma-separated strings into lists
    docs_list = [d.strip() for d in relevant_docs.split(",")] if relevant_docs else []
    points_list = [p.strip() for p in key_points.split(",")] if key_points else []
    
    proposed_response = {
        "message": message,
        "reasoning": reasoning,
        "suggested_tone": suggested_tone,
        "relevant_docs": docs_list,
        "key_points": points_list
    }
    
    return Command(
        update={
            "proposed_response": proposed_response,
            "messages": [ToolMessage(
                content=f"Proposed response set successfully.\n\nMessage preview: {message[:100]}{'...' if len(message) > 100 else ''}\nTone: {suggested_tone}\nKey points: {len(points_list)}",
                tool_call_id=tool_call_id
            )]
        }
    )


@tool
def add_accessed_document(
    doc_reference: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[Dict, InjectedState]
) -> Command[Literal["call_model"]]:
    """Track that a documentation file was accessed during reasoning.
    
    Args:
        doc_reference: Reference to the document (e.g., 'blueprint.md', 'faq.md#pharmacy')
    
    Returns:
        Confirmation message
    """
    current_docs = state.get("accessed_documents", [])
    
    # Add if not already tracked
    if doc_reference not in current_docs:
        updated_docs = current_docs + [doc_reference]
    else:
        updated_docs = current_docs
    
    return Command(
        update={
            "accessed_documents": updated_docs,
            "messages": [ToolMessage(
                content=f"Tracked access to: {doc_reference}",
                tool_call_id=tool_call_id
            )]
        }
    )


async def _load_tools() -> List[BaseTool]:
    """Load all available tools from the MCP gateway.
    
    Returns:
        List of LangChain tools
    """
    logger.info("Loading tools from gateway")
    tools = []
    tool_names = []
    for tool_def in await mcp_client.list_tools():
        logger.info(f"Loading tool: {tool_def['name']}")
        if tool_def['name'] in tool_names:
            continue

        tool_names.append(tool_def['name'])
        tool = _create_tool_wrapper(tool_def)
        tools.append(tool)

    logger.info(tool_names)
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
    
    # Local state management tools
    local_tools = [
        get_conversation_history,
        get_escalation_context,
        set_proposed_response,
        add_accessed_document
    ]
    
    # Configure MCP client with gateway URL from config
    if hasattr(config, "mcp_gateway_url"):
        mcp_client.get_client(config.mcp_gateway_url)
    
    # Load MCP tools from gateway
    mcp_tools = await _load_tools()
    
    # Merge local and MCP tools
    TOOLS = local_tools + mcp_tools

    logger.info(f"Initialized {len(local_tools)} local tools and {len(mcp_tools)} MCP tools")
    return TOOLS
