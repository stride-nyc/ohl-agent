import os
import sys
from pathlib import Path

# Add src to path to import directly without triggering graph initialization
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from react_agent.configuration import Configuration


def test_configuration_empty() -> None:
    Configuration.from_runnable_config({})


def test_configuration_azure_fields_exist() -> None:
    """Test that Azure configuration fields exist on Configuration dataclass."""
    config = Configuration()

    # Test that azure fields exist
    assert hasattr(config, "azure_endpoint")
    assert hasattr(config, "azure_api_version")
    assert hasattr(config, "azure_deployment")


def test_configuration_azure_defaults_from_env(monkeypatch) -> None:
    """Test that Azure configuration loads defaults from environment variables."""
    # Set environment variables
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4-test")

    # Create config and verify values loaded from env
    config = Configuration()
    assert config.azure_endpoint == "https://test.openai.azure.com/"
    assert config.azure_api_version == "2024-08-01-preview"
    assert config.azure_deployment == "gpt-4-test"


def test_configuration_azure_fallback_defaults(monkeypatch) -> None:
    """Test that Azure configuration has proper fallback defaults when env vars not set."""
    # Clear Azure environment variables
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)

    config = Configuration()

    # azure_endpoint and azure_deployment should be None when not configured
    assert config.azure_endpoint is None
    assert config.azure_deployment is None

    # azure_api_version should have a sensible default
    assert config.azure_api_version == "2024-02-15-preview"
