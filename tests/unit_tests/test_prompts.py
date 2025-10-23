"""Tests for system prompt configuration."""

from react_agent.prompts import SYSTEM_PROMPT


def test_system_prompt_includes_explicit_length_limit():
    """Test that system prompt includes EXPLICIT numerical length constraints.

    Based on analysis of docs/samples.md and user feedback:
    - Templates are 8-83 words but need room for personalization
    - Adjusted target: 75-150 words typical, max 200 words
    - Prevents overly formulaic responses while maintaining conciseness

    Without explicit limits, LLM generates 2,819 token (2,100+ word) responses taking 34+ seconds.
    """
    prompt_lower = SYSTEM_PROMPT.lower()

    # Should mention specific word counts in a length constraint context
    # Check for "X words" or "X-Y words" patterns
    import re
    word_limit_patterns = [
        r'50[\s-]+word',
        r'75[\s-]+word',
        r'100[\s-]+word',
        r'125[\s-]+word',
        r'150[\s-]+word',
        r'200[\s-]+word',
        r'maximum.*\d+.*word',
        r'\d+[\s]*-[\s]*\d+[\s]+word'
    ]

    has_explicit_limit = any(re.search(pattern, prompt_lower) for pattern in word_limit_patterns)

    assert has_explicit_limit, \
        "System prompt must include EXPLICIT word count limits (e.g., '75-150 words', 'maximum 200 words'). " \
        "Templates are short but agent needs room for personalization and context. " \
        "Vague 'be concise' results in 2,100+ word responses."


def test_system_prompt_includes_verbatim_language_requirement():
    """Test that system prompt still requires verbatim language from docs.

    Conciseness should not compromise the verbatim language requirement.
    """
    prompt_lower = SYSTEM_PROMPT.lower()

    assert "verbatim" in prompt_lower, \
        "System prompt should require verbatim language from documentation"
