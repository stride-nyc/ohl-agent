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
- `retrieve_context`: Get conversation history, escalation context, and preloaded docs confirmation in ONE call
- `submit_response`: Submit final proposed message and track accessed documents in ONE call

#### Documentation (Preloaded)
All documentation is preloaded into the system prompt at startup for optimal performance:
- `blueprint.md`: Welcome call campaign script with structured talking points
- `faq.md`: Common member questions and templated responses
- `samples.md`: Live chat response templates for various scenarios

No MCP calls needed during the reasoning loop, resulting in 60-70% faster response times.

### Execution Flow & Call Stack

This section explains how a request flows through the system from startup to response generation.

#### Startup Sequence

```
langgraph dev
  └─> LangGraph Server starts (port 2024)
      └─> Loads langgraph.json
          └─> Imports react_agent.graph.py:graph
              └─> MODULE INITIALIZATION
                  ├─> prompts.py imports (line 3)
                  │   └─> load_documentation() executes (prompts.py:6)
                  │       ├─> Reads docs/blueprint.md
                  │       ├─> Reads docs/faq.md
                  │       ├─> Reads docs/samples.md
                  │       ├─> Escapes curly braces for format() safety
                  │       └─> Returns _PRELOADED_DOCS string
                  │           └─> Injected into SYSTEM_PROMPT (prompts.py:108)
                  │
                  ├─> Configuration.load_from_langgraph_json() (graph.py:22-23)
                  │   └─> Sets mcp_gateway_url = "http://localhost:8808"
                  │
                  └─> asyncio.run(initialize_tools(config))
                      ├─> Local tools: [retrieve_context, submit_response]
                      │
                      └─> MCP tools via mcp_client.list_tools()
                          └─> HTTP POST to gateway:8808/message
                              └─> Returns memory tools (filesystem not needed for docs)
```

**Parallel Process - MCP Gateway** (port 8808):
```bash
cd gateway && python3 -m mcp_gateway.server
  ├─> Loads gateway/config.json
  ├─> Spawns MCP server subprocesses
  │   ├─> npx @modelcontextprotocol/server-filesystem ../ohl-agent-docs
  │   └─> npx @modelcontextprotocol/server-memory
  └─> Listens on port 8808 for tool requests
```

#### Request Processing Flow

When a request arrives at `POST http://localhost:2024/runs/stream`:

**1. State Initialization**
```
LangGraph Runtime
  └─> Creates State from InputState (state.py)
      ├─> messages: [HumanMessage("Please analyze...")]
      ├─> conversation_history: [ConversationMessage(...), ...]
      ├─> escalation_context: EscalationContext(...)
      ├─> proposed_response: None
      └─> accessed_documents: []
```

**2. StateGraph Execution**

The agent uses a ReAct (Reasoning and Acting) pattern:

```
__start__ → call_model → [route] → __end__
               ↑            ↓
               └─── tools ──┘
```

**3. The ReAct Loop**

**Node: `call_model` (graph.py:25-75)**

```
call_model(state, config)
  │
  ├─> 1. Load Configuration
  │      configuration = Configuration.from_runnable_config(config)
  │      └─> Extracts: model, azure_*, system_prompt, etc.
  │
  ├─> 2. Initialize LLM (lines 42-48)
  │      model = load_chat_model(
  │          model_name="azure/gpt-4",  # or anthropic/openai/openrouter
  │          azure_endpoint=...,
  │          ...
  │      ).bind_tools(TOOLS)
  │      │
  │      └─> utils.py:load_chat_model()
  │          ├─> Parses "provider/model" pattern
  │          └─> Routes to provider:
  │              ├─> azure → AzureChatOpenAI(endpoint, deployment, key, version)
  │              ├─> anthropic → ChatAnthropic(model)
  │              ├─> openai → ChatOpenAI(model)
  │              └─> openrouter → ChatOpenAI(base_url)
  │
  ├─> 3. Format System Prompt
  │      system_message = configuration.system_prompt.format(
  │          system_time=datetime.now().isoformat()
  │      )
  │
  ├─> 4. Invoke LLM
  │      response = await model.ainvoke([
  │          {"role": "system", "content": system_message},
  │          *state["messages"]
  │      ])
  │      │
  │      └─> LLM decides:
  │          ├─> Option A: Return text (no tools) → __end__
  │          └─> Option B: Request tools → tools node
  │
  └─> 5. Return Response
         return {"messages": [response]}
```

**Conditional Routing: `route_model_output` (graph.py:90-110)**

```python
if not last_message.tool_calls:
    return "__end__"        # Finish execution
else:
    return "tools"          # Execute tools, continue loop
```

**Node: `tools` (graph.py:83)** - If tools requested

```
ToolNode(TOOLS)
  └─> For each tool_call in response.tool_calls:
      │
      ├─> retrieve_context (Consolidated State Tool)
      │   └─> tools.py:122-178
      │       ├─> Reads state["conversation_history"]
      │       ├─> Reads state["escalation_context"]
      │       ├─> Confirms preloaded docs available in system prompt
      │       └─> Returns Command(update={
      │             "messages": [ToolMessage(
      │               content="# RETRIEVED CONTEXT\n\n## Conversation History...\n\n## Escalation Context...\n\n## Preloaded Documentation\nAll documentation has been preloaded..."
      │             )]
      │           })
      │
      ├─> submit_response (Consolidated Output Tool)
      │   └─> tools.py:181-230
      │       ├─> Validates message, reasoning, tone, relevant_docs, key_points
      │       ├─> Updates state["proposed_response"]
      │       ├─> Updates state["accessed_documents"]
      │       └─> Returns Command(update={...})
      │
      └─> MCP Tool (e.g., memory operations - if configured)
          └─> tools.py:_create_tool_wrapper()
              └─> mcp_client.call_tool("memory_operation", {...})
                  └─> HTTP POST to gateway:8808/message
                      └─> MCP Gateway routes to memory server

  └─> Tool results appended to state["messages"]
      └─> Edge: tools → call_model (LOOP CONTINUES)
```

**4. Loop Termination**

The agent cycles through `call_model` → `tools` → `call_model` until:
- Model returns a response without tool calls
- Recursion limit reached (default: 50)
- `is_last_step=True` safety check triggers

**5. Final State & Response**

```
Final State:
{
  "messages": [
    HumanMessage("Please analyze..."),
    AIMessage("I'll check the docs", tool_calls=[...]),
    ToolMessage("Blueprint contents: ..."),
    AIMessage("Based on the docs, I'll set the response"),
    ToolMessage("Response set successfully")
  ],
  "proposed_response": {
    "message": "I understand your frustration...",
    "reasoning": "Member is frustrated due to...",
    "suggested_tone": "empathetic_and_solution_focused",
    "relevant_docs": ["samples.md#apologies"],
    "key_points": [...]
  },
  "accessed_documents": ["docs/blueprint.md", "docs/samples.md"]
}

LangGraph streams response via Server-Sent Events:
  - Event: metadata (run_id)
  - Event: messages (each AI/Tool message)
  - Event: debug (node execution)
  - Event: values (final state)
  - Event: end
```

#### Key Architectural Patterns

**1. State Injection for Local Tools**
```python
@tool
def get_conversation_history(
    state: Annotated[dict, InjectedState]  # LangGraph injects current state
) -> Command:
    return Command(update={"messages": [...]})  # Updates state
```

**2. MCP Tool Wrapping**
```python
def _create_tool_wrapper(tool_def: Dict) -> BaseTool:
    async def wrapper(**kwargs):
        result = await mcp_client.call_tool(name, kwargs)  # HTTP to gateway
        return result
    return StructuredTool(name=..., func=wrapper, args_schema=...)
```

**3. Provider Abstraction**
```python
def load_chat_model(model_name: str, **provider_config):
    provider, model = model_name.split("/")  # "azure/gpt-4"

    if provider == "azure":
        return AzureChatOpenAI(...)
    elif provider == "anthropic":
        return ChatAnthropic(...)
    # ... etc
```

#### Complete Call Stack

```
User HTTP Request
  └─> LangGraph Server (port 2024)
      └─> StateGraph.compile().ainvoke()
          └─> __start__ node
              └─> call_model node
                  ├─> Configuration.from_runnable_config()
                  ├─> load_chat_model()
                  │   └─> AzureChatOpenAI(...) or ChatAnthropic(...) or ChatOpenAI(...)
                  ├─> model.bind_tools(TOOLS)
                  └─> model.ainvoke([system_prompt, *messages])
                      └─> route_model_output()
                          ├─> IF no tool_calls → __end__
                          └─> IF tool_calls → tools node
                              └─> ToolNode(TOOLS)
                                  ├─> Local Tool → Command(update={...})
                                  └─> MCP Tool → HTTP to gateway:8808
                                      └─> MCP Gateway → MCP Server
                                          └─> Tool execution → ToolMessage
                                              └─> Edge: tools → call_model (LOOP)
```

This architecture enables:
- ✅ **Separation of concerns**: LLM reasoning separate from tool execution
- ✅ **Extensibility**: Easy to add new tools via MCP or local functions
- ✅ **Provider flexibility**: Swap LLM providers via configuration
- ✅ **State management**: Clean state updates via Command pattern
- ✅ **Observability**: LangSmith tracing of entire execution flow

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

### 1. High-Performance Documentation Access
- **Preloaded Documentation**: All docs loaded into system prompt at startup for instant access
- **60-70% Faster Response Times**: Eliminates HTTP round-trips to MCP gateway during reasoning
- **50-60% Cost Reduction**: Fewer LLM calls due to consolidated tools
- **Verbatim Language Usage**: Agent uses exact phrases from documentation for consistency
- Tracks which documents were referenced in responses

### 2. Consolidated Tool Architecture
- **2 Optimized Tools**: `retrieve_context` and `submit_response` replace 4 separate tools
- **Single-Call Context Retrieval**: Get conversation history, escalation context, and docs confirmation in one call
- **Single-Call Response Submission**: Set response and track documents in one call
- Reduces reasoning chain length and LLM token usage

### 3. Structured Input/Output
- Clear separation between conversation history and escalation context
- Structured output with message, reasoning, tone, and references
- Easy integration with existing systems

### 4. Compliance-Aware
- System prompt emphasizes required disclaimers
- Documentation includes compliance requirements
- Agent trained to include necessary legal language

### 5. State Injection Pattern
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
2. Update `load_documentation()` in `src/react_agent/docs_loader.py` to include new files in `required_docs` list
3. Update the system prompt in `src/react_agent/prompts.py` to reference new documentation if needed
4. **Restart LangGraph dev server** - Documentation is loaded at module initialization, not dynamically

**Important**: Unlike MCP-based approaches, documentation changes require a server restart to take effect.

### Modifying Response Structure
1. Update `ProposedResponse` dataclass in `src/react_agent/state.py`
2. Update `submit_response` tool in `src/react_agent/tools.py`
3. Update system prompt to reflect new structure

### Changing Documentation Location
Update the `docs_dir` parameter in `load_documentation()` call or set `DOCS_DIR` environment variable:

**Option 1: Modify prompts.py**
```python
# src/react_agent/prompts.py
_PRELOADED_DOCS = load_documentation(docs_dir="/path/to/your/docs")
```

**Option 2: Use environment variable**
```bash
# .env
DOCS_DIR=/path/to/your/docs
```

Then update `docs_loader.py` to read from `os.getenv("DOCS_DIR")` if provided.

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
