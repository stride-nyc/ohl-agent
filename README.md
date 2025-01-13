# LangGraph ReAct Agent with MCP

[![CI](https://github.com/langchain-ai/react-agent/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/react-agent/actions/workflows/unit-tests.yml)
[![Integration Tests](https://github.com/langchain-ai/react-agent/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/langchain-ai/react-agent/actions/workflows/integration-tests.yml)
[![Open in - LangGraph Studio](https://img.shields.io/badge/Open_in-LangGraph_Studio-00324d.svg?logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4NS4zMzMiIGhlaWdodD0iODUuMzMzIiB2ZXJzaW9uPSIxLjAiIHZpZXdCb3g9IjAgMCA2NCA2NCI+PHBhdGggZD0iTTEzIDcuOGMtNi4zIDMuMS03LjEgNi4zLTYuOCAyNS43LjQgMjQuNi4zIDI0LjUgMjUuOSAyNC41QzU3LjUgNTggNTggNTcuNSA1OCAzMi4zIDU4IDcuMyA1Ni43IDYgMzIgNmMtMTIuOCAwLTE2LjEuMy0xOSAxLjhtMzcuNiAxNi42YzIuOCAyLjggMy40IDQuMiAzLjQgNy42cy0uNiA0LjgtMy40IDcuNkw0Ny4yIDQzSDE2LjhsLTMuNC0zLjRjLTQuOC00LjgtNC44LTEwLjQgMC0xNS4ybDMuNC0zLjRoMzAuNHoiLz48cGF0aCBkPSJNMTguOSAyNS42Yy0xLjEgMS4zLTEgMS43LjQgMi41LjkuNiAxLjcgMS44IDEuNyAyLjcgMCAxIC43IDIuOCAxLjYgNC4xIDEuNCAxLjkgMS40IDIuNS4zIDMuMi0xIC42LS42LjkgMS40LjkgMS41IDAgMi43LS41IDIuNy0xIDAtLjYgMS4xLS44IDIuNi0uNGwyLjYuNy0xLjgtMi45Yy01LjktOS4zLTkuNC0xMi4zLTExLjUtOS44TTM5IDI2YzAgMS4xLS45IDIuNS0yIDMuMi0yLjQgMS41LTIuNiAzLjQtLjUgNC4yLjguMyAyIDEuNyAyLjUgMy4xLjYgMS41IDEuNCAyLjMgMiAyIDEuNS0uOSAxLjItMy41LS40LTMuNS0yLjEgMC0yLjgtMi44LS44LTMuMyAxLjYtLjQgMS42LS41IDAtLjYtMS4xLS4xLTEuNS0uNi0xLjItMS42LjctMS43IDMuMy0yLjEgMy41LS41LjEuNS4yIDEuNi4zIDIuMiAwIC43LjkgMS40IDEuOSAxLjYgMi4xLjQgMi4zLTIuMy4yLTMuMi0uOC0uMy0yLTEuNy0yLjUtMy4xLTEuMS0zLTMtMy4zLTMtLjUiLz48L3N2Zz4=)](https://langgraph-studio.vercel.app/templates/open?githubUrl=https://github.com/langchain-ai/react-agent)

This template showcases a [ReAct agent](https://arxiv.org/abs/2210.03629) implemented using [LangGraph](https://github.com/langchain-ai/langgraph) and the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). The agent uses MCP servers to provide tools and capabilities through a unified gateway.

## Architecture

The system consists of three main components:

1. **MCP Gateway Server**: A server that:
   - Manages multiple MCP server processes
   - Provides a unified API for accessing tools
   - Handles communication with MCP servers
   - Exposes tools through a simple HTTP interface

2. **MCP Servers**: Individual servers that provide specific capabilities:
   - Filesystem Server: File operations (read, write, list, search)
   - Memory Server: Knowledge graph operations (entities, relations, queries)
   - Additional servers can be added for more capabilities

3. **ReAct Agent**: The agent that:
   - Connects to the MCP gateway
   - Discovers available tools
   - Uses tools to accomplish tasks
   - Combines capabilities from multiple servers

## Getting Started

### 1. Install Dependencies

```bash
# Install the agent package
pip install -e .

# Install the gateway package
cd gateway
pip install -e .
cd ..
```

### 2. Configure MCP Servers

The gateway server is configured through `gateway/config.json`. By default, it starts two MCP servers:

```json
{
  "mcp": {
    "servers": {
      "filesystem": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-filesystem",
          "/path/to/directory"
        ]
      },
      "memory": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-memory"
        ]
      }
    }
  }
}
```

You can add more servers from the [official MCP servers repository](https://github.com/modelcontextprotocol/servers).

### 3. Start the Gateway Server

```bash
cd gateway
python -m mcp_gateway.server
```

The server will start on port 8808 by default.

### 4. Configure the Agent

The agent's connection to the gateway is configured in `langgraph.json`:

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/react_agent/graph.py:graph"
  },
  "env": ".env",
  "mcp": {
    "gateway_url": "http://localhost:8808"
  }
}
```

### 5. Use the Agent

Open your app in LangGraph!  Install guide [here](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/#launch-langgraph-server).  

This will open a new browser window with the agent running.  The agent will automatically:
1. Connect to the local gateway server
2. Discover available tools
3. Make tools available for use in conversations

## Available Tools

The agent has access to tools from both MCP servers:

### Filesystem Tools
- `read_file`: Read file contents
- `write_file`: Create or update files
- `list_directory`: List directory contents
- `search_files`: Find files matching patterns
- And more...

### Memory Tools
- `create_entities`: Add entities to knowledge graph
- `create_relations`: Link entities together
- `search_nodes`: Query the knowledge graph
- And more...

## Development

### Adding New MCP Servers

1. Find a server in the [MCP servers repository](https://github.com/modelcontextprotocol/servers)
2. Add its configuration to `gateway/config.json`
3. The agent will automatically discover its tools

### Customizing the Agent

- Modify the system prompt in `src/react_agent/prompts.py`
- Update the agent's reasoning in `src/react_agent/graph.py`
- Add new capabilities by including more MCP servers

## Documentation

- [LangGraph Documentation](https://github.com/langchain-ai/langgraph)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
