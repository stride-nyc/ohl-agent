"""Tests for documentation loader module."""

import os
import tempfile
from pathlib import Path
import pytest

# Import directly to avoid triggering full module initialization
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from react_agent.docs_loader import load_documentation


def test_load_documentation_missing_directory():
    """Test that load_documentation handles missing directory gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent_dir = os.path.join(tmpdir, "nonexistent")

        # Should not raise, should return empty string (dev/test mode)
        result = load_documentation(docs_dir=nonexistent_dir)

        assert result is not None
        assert isinstance(result, str)
        # Empty string returned when docs unavailable (allows module to load)
        assert result == ""


def test_load_documentation_empty_directory():
    """Test that load_documentation handles empty directory gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Empty directory exists but has no markdown files
        result = load_documentation(docs_dir=tmpdir)

        assert result is not None
        assert isinstance(result, str)
        # Empty string returned when no docs available (allows module to load)
        assert result == ""


def test_load_documentation_partial_files():
    """Test that load_documentation handles missing required files gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create only one of the required files
        blueprint_path = Path(tmpdir) / "blueprint.md"
        blueprint_path.write_text("# Blueprint\nSome content")

        # Missing faq.md and samples.md
        result = load_documentation(docs_dir=tmpdir)

        assert result is not None
        assert isinstance(result, str)
        assert "DOCUMENTATION UNAVAILABLE" in result or "PARTIAL DOCUMENTATION" in result


def test_load_documentation_success():
    """Test that load_documentation works correctly with all files present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create all required files
        (Path(tmpdir) / "blueprint.md").write_text("# Blueprint\nWelcome call script")
        (Path(tmpdir) / "faq.md").write_text("# FAQ\nCommon questions")
        (Path(tmpdir) / "samples.md").write_text("# Samples\nResponse templates")

        result = load_documentation(docs_dir=tmpdir)

        assert result is not None
        assert isinstance(result, str)
        assert "PRELOADED DOCUMENTATION" in result
        assert "blueprint.md" in result
        assert "faq.md" in result
        assert "samples.md" in result
        assert "Welcome call script" in result
        assert "Common questions" in result
        assert "Response templates" in result


def test_load_documentation_escapes_curly_braces():
    """Test that curly braces in documentation are properly escaped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files with curly braces (like markdown anchors)
        (Path(tmpdir) / "blueprint.md").write_text("# Section {#anchor}")
        (Path(tmpdir) / "faq.md").write_text("# FAQ {#faq-section}")
        (Path(tmpdir) / "samples.md").write_text("# Samples {#samples}")

        result = load_documentation(docs_dir=tmpdir)

        # Curly braces should be escaped for format string safety
        assert "{{#anchor}}" in result
        assert "{{#faq-section}}" in result
        assert "{{#samples}}" in result


def test_load_documentation_default_path_behavior():
    """Test that load_documentation uses sensible defaults when no path provided."""
    # This test documents expected behavior when docs_dir=None
    # Should either find docs or gracefully degrade
    result = load_documentation(docs_dir=None)

    # Should return string, not raise exception
    assert result is not None
    assert isinstance(result, str)
    # Either loaded successfully (PRELOADED DOCUMENTATION) or degraded gracefully (empty string)
    assert "PRELOADED DOCUMENTATION" in result or result == ""
