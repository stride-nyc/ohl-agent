"""Pytest configuration and fixtures for ohl-agent tests."""

import sys
from unittest.mock import AsyncMock, patch

# Mock MCP initialization BEFORE any imports of react_agent modules
# This prevents the MCP gateway connection attempt during module import
mock_init_tools = AsyncMock(return_value=None)
sys.modules.setdefault('react_agent.tools', type(sys)('react_agent.tools'))
if 'react_agent.tools' in sys.modules:
    sys.modules['react_agent.tools'].initialize_tools = mock_init_tools
    sys.modules['react_agent.tools'].TOOLS = []
