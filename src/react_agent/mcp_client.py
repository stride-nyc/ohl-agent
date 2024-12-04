"""MCP client management for ReAct Agent."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable, Awaitable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

from react_agent.configuration import Configuration, MCPServerConfig


@dataclass
class MCPServer:
    """Represents a running MCP server and its capabilities."""
    name: str
    config: MCPServerConfig
    session: ClientSession
    tools: List[Tool]
    process: asyncio.subprocess.Process


class MCPClientManager:
    """Manages MCP server processes and client sessions."""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        
    async def start_server(self, name: str, config: MCPServerConfig) -> MCPServer:
        """Start an MCP server and initialize its client session."""
        # Create server parameters
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args
        )
        
        # Start the server process and create client session
        async with stdio_client(server_params) as (read, write):
            session = ClientSession(read, write)
            await session.initialize()
            
            # Query available tools
            tools = await session.list_tools()
            
            # Store server info
            server = MCPServer(
                name=name,
                config=config,
                session=session,
                tools=tools,
                process=server_params.process
            )
            self.servers[name] = server
            return server
    
    async def start_all_servers(self, config: Configuration) -> None:
        """Start all configured MCP servers."""
        for name, server_config in config.mcp_servers.items():
            await self.start_server(name, server_config)
    
    def create_tool_wrapper(
        self,
        server: MCPServer,
        tool: Tool
    ) -> Callable[..., Awaitable[Any]]:
        """Create a wrapper function for an MCP tool that can be used by the agent."""
        
        async def wrapper(**kwargs) -> Any:
            """Wrapper function that calls the MCP tool."""
            result = await server.session.call_tool(
                tool.name,
                arguments=kwargs
            )
            return result
            
        # Set metadata on wrapper function
        wrapper.__name__ = f"{server.name}_{tool.name}"
        wrapper.__doc__ = tool.description
        
        return wrapper
    
    def get_all_tools(self) -> List[Callable[..., Any]]:
        """Get all available tools from all servers."""
        tools = []
        for server in self.servers.values():
            for tool in server.tools:
                wrapper = self.create_tool_wrapper(server, tool)
                tools.append(wrapper)
        return tools
    
    async def shutdown(self) -> None:
        """Shutdown all MCP servers."""
        for server in self.servers.values():
            if server.process:
                server.process.terminate()
                await server.process.wait()
        self.servers.clear()
