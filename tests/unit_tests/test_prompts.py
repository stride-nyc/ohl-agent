"""Tests for system prompt configuration."""

from react_agent.prompts import SYSTEM_PROMPT


def test_system_prompt_includes_explicit_length_limit():
    """Test that system prompt includes EXPLICIT numerical length constraints.

    Based on analysis of docs/samples.md:
    - Actual chat responses: 8-83 words, median 25 words
    - Longest sample: 83 words (complex benefit explanation)

    Agent responses should match this pattern: 50-100 words typical, max 125 words.
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
        r'maximum.*\d+.*word',
        r'\d+[\s]*-[\s]*\d+[\s]+word'
    ]

    has_explicit_limit = any(re.search(pattern, prompt_lower) for pattern in word_limit_patterns)

    assert has_explicit_limit, \
        "System prompt must include EXPLICIT word count limits (e.g., '50-100 words', 'maximum 125 words'). " \
        "Documentation analysis shows actual responses are 8-83 words (median 25). " \
        "Vague 'be concise' results in 2,100+ word responses."


def test_system_prompt_includes_verbatim_language_requirement():
    """Test that system prompt still requires verbatim language from docs.

    Conciseness should not compromise the verbatim language requirement.
    """
    prompt_lower = SYSTEM_PROMPT.lower()

    assert "verbatim" in prompt_lower, \
        "System prompt should require verbatim language from documentation"
