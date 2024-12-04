"""Define the configurable parameters for the agent."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from typing import Annotated, Optional, Dict, List

from langchain_core.runnables import RunnableConfig, ensure_config

from react_agent import prompts


class ConfigurationError(Exception):
    """Raised when there is an error in the configuration."""
    pass


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    command: str
    args: List[str]


@dataclass(kw_only=True)
class Configuration:
    """The configuration for the agent."""

    system_prompt: str = field(
        default=prompts.SYSTEM_PROMPT,
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent."
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="anthropic/claude-3-5-sonnet-20240620",
        metadata={
            "description": "The name of the language model to use for the agent's main interactions. "
            "Should be in the form: provider/model-name."
        },
    )

    max_search_results: int = field(
        default=10,
        metadata={
            "description": "The maximum number of search results to return for each search query."
        },
    )

    mcp_servers: Dict[str, MCPServerConfig] = field(
        default_factory=dict,
        metadata={
            "description": "Configuration for MCP servers that provide tools and capabilities."
        },
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}
        
        # Handle MCP server configs if present
        if "mcp_servers" in configurable:
            raw_servers = configurable["mcp_servers"]
            configurable["mcp_servers"] = {
                name: MCPServerConfig(**cfg)
                for name, cfg in raw_servers.items()
            }
        
        return cls(**{k: v for k, v in configurable.items() if k in _fields})

    @classmethod
    def load_from_langgraph_json(cls) -> Configuration:
        """Load configuration from langgraph.json file."""
        # Find langgraph.json in current directory or parent directories
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir != '/':
            config_path = os.path.join(current_dir, 'langgraph.json')
            if os.path.exists(config_path):
                break
            current_dir = os.path.dirname(current_dir)
        else:
            raise FileNotFoundError("Could not find langgraph.json")

        # Load and parse the config file
        with open(config_path, 'r') as f:
            config_data = json.load(f)

        # Create configuration instance
        config = cls()

        # Load MCP server configurations if present
        if 'mcp' in config_data and 'servers' in config_data['mcp']:
            config.mcp_servers = {
                name: MCPServerConfig(**server_config)
                for name, server_config in config_data['mcp']['servers'].items()
            }

        # Validate MCP servers are configured
        if not config.mcp_servers:
            raise ConfigurationError(
                "No MCP servers defined in langgraph.json. "
                "At least one MCP server must be configured to provide tools for the ReAct agent."
            )

        return config
