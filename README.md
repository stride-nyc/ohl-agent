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

### 1. Install Dependencies

```bash
# Install the agent package
pip install -e .

# Install the gateway package
cd gateway
pip install -e .
cd ..
```

### 2. Start the Gateway Server

```bash
cd gateway
python -m mcp_gateway.server
```

The server will start on port 8808 and provide access to the File System MCP server (pointing to the `docs/` directory).

### 3. Use the Agent via LangGraph API

The agent is invoked via the LangGraph API with a structured payload:

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

### 4. Response Format

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

## Documentation

- [LangGraph Documentation](https://github.com/langchain-ai/langgraph)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
