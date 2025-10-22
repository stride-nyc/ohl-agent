# Medicare Insurance Helper Agent - LangGraph ReAct Agent with MCP

[![CI](https://github.com/langchain-ai/react-agent/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/react-agent/actions/workflows/unit-tests.yml)
[![Integration Tests](https://github.com/langchain-ai/react-agent/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/langchain-ai/react-agent/actions/workflows/integration-tests.yml)

This is a specialized [ReAct agent](https://arxiv.org/abs/2210.03629) built with [LangGraph](https://github.com/langchain-ai/langgraph) and the [Model Context Protocol (MCP)](https://modelcontextprotocol.io) to assist human agents with escalated Medicare insurance member conversations.

## Overview

The agent analyzes conversations between members and automated systems, then provides structured guidance to human agents on how to respond. It uses documentation (welcome call scripts, FAQs, response templates) to generate compliant, empathetic responses.

## Architecture

### Components

1. **MCP Gateway Server**: Manages MCP server processes and provides unified tool access
2. **File System MCP Server**: Provides access to documentation in the `docs/` directory
3. **ReAct Agent**: Analyzes conversations and generates proposed responses
4. **State Management Tools**: Local tools for reading/writing structured state

### State Structure

The agent uses a structured state system with:

- **conversation_history**: Messages between member and automated system
- **escalation_context**: Why escalated (reason, urgency, member sentiment)
- **proposed_response**: Agent's suggested message with reasoning, tone, and references
- **accessed_documents**: Tracking of documentation used

### Available Tools

#### State Management Tools (Local)
- `get_conversation_history`: Retrieve the full conversation
- `get_escalation_context`: Get escalation details
- `set_proposed_response`: Set the final proposed message
- `add_accessed_document`: Track documentation access

#### Documentation Tools (via MCP)
- File system access to `docs/` directory containing:
  - `blueprint.md`: Welcome call campaign script
  - `faq.md`: Common member questions and answers
  - `samples.md`: Response templates for various scenarios

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip for package management
- Node.js and npm (for MCP servers)
- An API key for your chosen LLM provider:
  - **Anthropic** (Claude models)
  - **OpenAI** (GPT models)
  - **Azure OpenAI** (Azure-hosted GPT models)
  - **OpenRouter** (Access to multiple providers)

### 1. Setup Environment

Create a `.env` file in the project root with your API keys:

```bash
# LLM Configuration - supports openai, anthropic, openrouter, azure
# Choose ONE provider by setting LLM_MODEL:

# Option 1: Anthropic (recommended)
LLM_MODEL=anthropic/claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=your_api_key_here

# Option 2: OpenAI
# LLM_MODEL=openai/gpt-4o
# OPENAI_API_KEY=your_openai_api_key

# Option 3: Azure OpenAI
# LLM_MODEL=azure/your-deployment-name
# AZURE_OPENAI_API_KEY=your_azure_api_key
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_API_VERSION=2024-10-21

# Option 4: OpenRouter
# LLM_MODEL=openrouter/anthropic/claude-3-5-sonnet-20241022
# OPENROUTER_API_KEY=your_openrouter_api_key
# OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# LangSmith Configuration - for tracing and monitoring (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key_here
LANGCHAIN_PROJECT=ohl-agent
```

#### Azure OpenAI Setup (Option 3)

If using Azure OpenAI, you need to gather configuration from your Azure Portal:

1. **AZURE_OPENAI_ENDPOINT**:
   - Go to your Azure OpenAI resource → "Keys and Endpoint"
   - Copy the "Endpoint" URL (e.g., `https://your-resource.openai.azure.com/`)

2. **AZURE_OPENAI_API_KEY**:
   - Same location → Copy "KEY 1" or "KEY 2"

3. **Deployment Name** (for `LLM_MODEL`):
   - Go to your Azure OpenAI resource → "Model deployments" (or Azure OpenAI Studio)
   - Find your deployment name (e.g., `gpt-4`, `gpt-35-turbo`, etc.)
   - **Important**: This is YOUR deployment name, not the model name
   - Set `LLM_MODEL=azure/your-deployment-name`

4. **AZURE_OPENAI_API_VERSION**:
   - Use a stable version like `2024-10-21` (recommended)
   - See [Azure OpenAI API versions](https://learn.microsoft.com/en-us/azure/ai-services/openai/api-version-deprecation) for latest

### 2. Create Documentation Directory

The MCP gateway needs access to documentation. Create a directory at the same level as the project:

```bash
# From the project root
cd ..
mkdir ohl-agent-docs
# Add your documentation files (blueprint.md, faq.md, samples.md) to this directory
cd ohl-agent
```

### 3. Install Dependencies

#### Option A: Using uv (Recommended)

```bash
# Create and activate virtual environment for the agent
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the agent package
uv pip install -e .

# Create and activate virtual environment for the gateway
cd gateway
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the gateway package
uv pip install -e .
cd ..
```

#### Option B: Using pip with venv

```bash
# Create and activate virtual environment for the agent
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the agent package
pip install -e .

# Create and activate virtual environment for the gateway
cd gateway
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the gateway package
pip install -e .
cd ..
```

### 4. Configure Gateway

Update `gateway/config.json` to use relative path to docs:

```json
{
  "mcp": {
    "servers": {
      "filesystem": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-filesystem",
          "../ohl-agent-docs"
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

### 5. Start the Servers

You need to run both servers. Open two terminal windows:

**Terminal 1 - MCP Gateway:**
```bash
cd gateway
source .venv/bin/activate  # Activate the gateway virtual environment
python3 -m mcp_gateway.server
```

The gateway will start on port 8808 and connect to the File System and Memory MCP servers.

**Terminal 2 - LangGraph Dev Server:**
```bash
# From the project root
source .venv/bin/activate  # Activate the agent virtual environment
langgraph dev
```

The LangGraph server will start on port 2024 and automatically:
- Load the agent graph
- Connect to the MCP gateway at http://localhost:8808
- Discover and load all available tools (local + MCP tools)

You should see output indicating:
- MCP Gateway started with filesystem and memory servers
- LangGraph server started and loaded tools
- Both servers ready to accept requests

### 6. Test the Agent

The agent can be invoked via the LangGraph API or through LangGraph Studio.

#### Via LangGraph Studio

Once both servers are running, LangGraph Studio will open in your browser at:
```
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

You can interact with the agent through the Studio UI by providing Medicare input.

#### Via API

The agent is invoked via HTTP POST to `http://localhost:2024/runs/stream` with a structured payload.

**IMPORTANT**: The `messages` field is required in the input. This field contains the initial prompt that instructs the agent to analyze the conversation. Even though the Medicare-specific data is in `conversation_history` and `escalation_context`, the agent needs at least one message in the `messages` array to start processing.

```json
{
  "input": {
    "messages": [
      {
        "content": "Please analyze this escalated conversation and provide guidance for the human agent.",
        "type": "human"
      }
    ],
    "conversation_history": [
      {
        "role": "member",
        "content": "I haven't received my ID card yet",
        "timestamp": "2025-01-20T10:00:00Z"
      },
      {
        "role": "system",
        "content": "Your card was mailed on January 5th",
        "timestamp": "2025-01-20T10:00:30Z"
      },
      {
        "role": "member",
        "content": "That was 3 weeks ago! I need it now!",
        "timestamp": "2025-01-20T10:01:00Z"
      }
    ],
    "escalation_context": {
      "reason": "member_frustrated",
      "urgency": "high",
      "member_sentiment": "frustrated"
    }
  },
  "config": {
    "tags": [],
    "recursion_limit": 50,
    "configurable": {}
  },
  "metadata": {},
  "stream_mode": ["debug", "messages"],
  "stream_subgraphs": true,
  "assistant_id": "agent",
  "interrupt_before": [],
  "interrupt_after": [],
  "multitask_strategy": "rollback"
}
```

### 4. Consuming the Streaming Response

The `/runs/stream` endpoint returns [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) that must be parsed to extract the agent's response. The stream includes multiple event types:

- **`metadata`**: Run metadata (run_id, etc.)
- **`messages`**: AI messages and tool calls as they're generated
- **`debug`**: Node execution lifecycle events (task start/completion)
- **`values`**: Complete state snapshots after each node execution
- **`error`**: Error events if execution fails
- **`end`**: Stream completion signal

**Key Requirements:**
1. Parse SSE format: Events are separated by `\n\n`, with `event:` and `data:` lines
2. Handle incremental updates: The agent state evolves as the stream progresses
3. Extract final state: The `proposed_response` field appears in the final `values` event

For detailed information on consuming the streaming API, see:
- [LangGraph Platform - Streaming](https://langchain-ai.github.io/langgraph/concepts/streaming/)
- [LangGraph API Reference - Runs](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/runs)

Alternatively, use the `/runs/wait` endpoint for a simpler non-streaming response that returns the complete final state in a single HTTP response.

### 5. Response Format

The agent returns a structured response in `state.proposed_response`:

```json
{
  "message": "I understand your frustration, [Member Name]. I'm truly sorry about the delay with your ID card. Let me help you right away. I can see that your card was mailed on January 5th, which is longer than our typical delivery time. I'd like to offer you two immediate solutions: First, I can help you print a temporary ID card from our member website right now, which you can use immediately. Second, I'll request a replacement card to be sent via expedited shipping. Would you like me to walk you through printing the temporary card?",
  
  "reasoning": "Member is frustrated due to delayed ID card delivery beyond normal timeframe. Using empathetic opening from samples.md#apologies-to-members, acknowledging the delay, and offering immediate actionable solutions per blueprint.md#verify-plan-information. Providing both immediate (temporary card) and long-term (replacement) solutions to address urgency.",
  
  "suggested_tone": "empathetic_and_solution_focused",
  
  "relevant_docs": [
    "samples.md#apologies-to-members",
    "blueprint.md#verify-plan-information",
    "faq.md#id-card-issues"
  ],
  
  "key_points": [
    "Acknowledge frustration and apologize for delay",
    "Explain the situation (card mailed but delayed)",
    "Offer immediate solution (temporary card)",
    "Offer long-term solution (expedited replacement)",
    "Provide clear next steps"
  ]
}
```

## Configuration

### MCP Gateway (`gateway/config.json`)

```json
{
  "mcp": {
    "servers": {
      "filesystem": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-filesystem",
          "/Users/dan/code/ohl-agent/docs"
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

### Agent Configuration (`langgraph.json`)

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

## Key Features

### 1. Documentation-Driven Responses
- Agent searches documentation for relevant guidance
- References specific sections in its reasoning
- Tracks which documents were accessed

### 2. Structured Input/Output
- Clear separation between conversation history and escalation context
- Structured output with message, reasoning, tone, and references
- Easy integration with existing systems

### 3. Compliance-Aware
- System prompt emphasizes required disclaimers
- Documentation includes compliance requirements
- Agent trained to include necessary legal language

### 4. State Injection Pattern
- Tools use LangGraph's `InjectedState` and `InjectedToolCallId`
- Returns `Command` objects for state updates
- Clean separation between local and MCP tools

## Customization

### Switching Between LLM Providers

You can easily switch between different LLM providers by updating the `LLM_MODEL` variable in your `.env` file:

**Switch to Anthropic Claude:**
```bash
LLM_MODEL=anthropic/claude-3-5-sonnet-20241022
# Ensure ANTHROPIC_API_KEY is set
```

**Switch to OpenAI GPT:**
```bash
LLM_MODEL=openai/gpt-4o
# Ensure OPENAI_API_KEY is set
```

**Switch to Azure OpenAI:**
```bash
LLM_MODEL=azure/your-deployment-name
# Ensure AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_API_VERSION are set
```

**Switch to OpenRouter:**
```bash
LLM_MODEL=openrouter/anthropic/claude-3-5-sonnet-20241022
# or
LLM_MODEL=openrouter/openai/gpt-4o
# Ensure OPENROUTER_API_KEY is set
```

After changing `LLM_MODEL`, restart the LangGraph dev server for changes to take effect.

### Adding New Documentation
1. Add markdown files to the `docs/` directory
2. The File System MCP server will automatically make them available
3. Update the system prompt in `src/react_agent/prompts.py` to reference new documentation

### Modifying Response Structure
1. Update `ProposedResponse` dataclass in `src/react_agent/state.py`
2. Update `set_proposed_response` tool in `src/react_agent/tools.py`
3. Update system prompt to reflect new structure

### Changing Documentation Location
Update the filesystem server path in `gateway/config.json`:
```json
{
  "mcp": {
    "servers": {
      "filesystem": {
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/new/path"]
      }
    }
  }
}
```

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit_tests/

# Integration tests
pytest tests/integration_tests/
```

### Local Development with LangGraph Studio

Install LangGraph Studio ([guide](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/#launch-langgraph-server)) and open this project. The agent will automatically:
1. Connect to the local gateway server
2. Discover available tools
3. Make tools available for use in conversations

## Troubleshooting

### Tools Not Loading
- Ensure MCP gateway is running on port 8808
- Check `gateway/config.json` for correct paths
- Review logs for tool initialization errors

### State Not Updating
- Verify tools return `Command` objects
- Check that `InjectedState` and `InjectedToolCallId` are properly annotated
- Ensure state field names match between tools and state classes

### Documentation Not Accessible
- Verify File System MCP server path in `gateway/config.json`
- Check that docs directory exists and contains markdown files
- Test MCP gateway directly: `curl http://localhost:8808/tools`

### Azure OpenAI Issues

#### Error: `DeploymentNotFound` (404)
**Problem**: "The API deployment for this resource does not exist"

**Solution**: Your deployment name is incorrect. The deployment name in `LLM_MODEL` must match exactly what's in Azure.

1. Go to Azure Portal → Your Azure OpenAI resource → "Model deployments"
2. Find the actual deployment name (e.g., `gpt-4`, `gpt-35-turbo`, or your custom name)
3. Update `.env`:
   ```bash
   LLM_MODEL=azure/your-actual-deployment-name
   AZURE_OPENAI_DEPLOYMENT=your-actual-deployment-name
   ```
4. **Common mistake**: Using the resource name instead of deployment name
   - ❌ Wrong: `ohlazureaihubd0505198248` (resource name)
   - ✅ Correct: `gpt-4` or `gpt-35-turbo` (deployment name)

#### Error: Authentication Failed (401)
**Problem**: Invalid or expired API key

**Solution**:
1. Verify `AZURE_OPENAI_API_KEY` in `.env` is correct
2. Check key hasn't been regenerated in Azure Portal
3. Ensure no extra spaces or quotes around the key

#### Error: Invalid API Version
**Problem**: API version is deprecated or invalid

**Solution**:
1. Update `AZURE_OPENAI_API_VERSION` to a current version (e.g., `2024-10-21`)
2. See [Azure OpenAI API versions](https://learn.microsoft.com/en-us/azure/ai-services/openai/api-version-deprecation)

#### Error: Endpoint Not Found
**Problem**: Incorrect endpoint URL format

**Solution**:
1. Verify endpoint format in `.env`:
   - ✅ Correct: `https://your-resource.openai.azure.com/`
   - ✅ Also valid: `https://your-resource.services.ai.azure.com/`
2. Must end with `/`
3. Must use `https://`

## Documentation

- [LangGraph Documentation](https://github.com/langchain-ai/langgraph)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
