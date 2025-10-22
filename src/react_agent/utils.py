"""Utility functions for the ReAct agent."""

import logging
import os
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_openai import AzureChatOpenAI, ChatOpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_chat_model(
    model_name: str,
    openrouter_base_url: str | None = None,
    azure_endpoint: str | None = None,
    azure_api_version: str | None = None,
    azure_deployment: str | None = None
) -> Any:
    """Load a chat model based on the provider prefix.

    Args:
        model_name: Name of the model in format "provider/model-name"
        openrouter_base_url: Base URL for OpenRouter API if using OpenRouter
        azure_endpoint: Azure OpenAI endpoint URL (required for Azure provider)
        azure_api_version: Azure OpenAI API version (required for Azure provider)
        azure_deployment: Azure OpenAI deployment name (optional, can be in model_name)

    Returns:
        A chat model instance

    Raises:
        ValueError: If the provider is not supported or required parameters are missing
    """
    logger.info(f"Loading chat model with name: {model_name}")
    provider, *model_parts = model_name.split("/")
    model = "/".join(model_parts)
    
    logger.info(f"Parsed provider: {provider}")
    logger.info(f"Parsed model: {model}")
    
    if provider == "anthropic":
        logger.info("Using Anthropic client")
        return ChatAnthropic(model=model)
    elif provider == "openai":
        logger.info("Using OpenAI client")
        return ChatOpenAI(model=model)
    elif provider == "openrouter":
        logger.info("Using OpenRouter via OpenAI client")
        logger.info(f"OpenRouter base URL: {openrouter_base_url}")
        
        if not openrouter_base_url:
            raise ValueError("openrouter_base_url is required for OpenRouter models")
            
        # For OpenRouter, we pass just the model part without the openrouter prefix
        api_key = os.getenv("OPENROUTER_API_KEY")
        logger.info(f"OpenRouter API key present: {bool(api_key)}")
        logger.info(f"Using model identifier: {model}")
        
        return ChatOpenAI(
            openai_api_key=api_key,
            openai_api_base=openrouter_base_url,
            model=model,  # Use just the model part (e.g., "anthropic/claude-3-5-sonnet-20241022")
        )
    elif provider == "azure":
        logger.info("Using Azure OpenAI client")
        logger.info(f"Azure endpoint: {azure_endpoint}")
        logger.info(f"Azure API version: {azure_api_version}")

        if not azure_endpoint:
            raise ValueError("azure_endpoint is required for Azure OpenAI models. "
                           "Set AZURE_OPENAI_ENDPOINT environment variable.")

        if not azure_api_version:
            raise ValueError("azure_api_version is required for Azure OpenAI models. "
                           "Set AZURE_OPENAI_API_VERSION environment variable.")

        # Deployment name can come from model string or azure_deployment parameter
        deployment_name = model or azure_deployment
        if not deployment_name:
            raise ValueError("Azure deployment name must be specified either in model string "
                           "(azure/deployment-name) or via AZURE_OPENAI_DEPLOYMENT environment variable.")

        logger.info(f"Using Azure deployment: {deployment_name}")

        # Get API key from environment
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable must be set for Azure OpenAI.")

        logger.info(f"Azure API key present: {bool(api_key)}")

        return AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            azure_deployment=deployment_name,
            api_key=api_key,
            api_version=azure_api_version,
        )
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            "Must be one of: anthropic, openai, openrouter, azure"
        )
