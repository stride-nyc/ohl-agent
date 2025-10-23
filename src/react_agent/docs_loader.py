"""Document loader for preloading documentation into system prompt."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_documentation(docs_dir: Optional[str] = None) -> str:
    """Load all documentation files and format them for the system prompt.

    Args:
        docs_dir: Path to the docs directory. If None, uses default location.

    Returns:
        Formatted string containing all documentation content, or fallback message
        if documentation is unavailable.
    """
    # Determine docs directory
    if docs_dir is None:
        # Default to docs/ directory relative to project root
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        docs_dir = project_root / "docs"
    else:
        docs_dir = Path(docs_dir)

    # Check if directory exists
    if not docs_dir.exists():
        logger.warning(f"Documentation directory not found: {docs_dir}. Using fallback.")
        return _get_fallback_documentation()

    logger.info(f"Loading documentation from: {docs_dir}")

    # Load each required document
    required_docs = ["blueprint.md", "faq.md", "samples.md"]
    doc_sections = []
    missing_docs = []

    for doc_name in required_docs:
        doc_path = docs_dir / doc_name
        if not doc_path.exists():
            logger.warning(f"Required documentation file not found: {doc_path}")
            missing_docs.append(doc_name)
            continue

        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Escape curly braces for Python's .format() method
                # This prevents markdown heading anchors like {#greetings:} from being interpreted as format placeholders
                content = content.replace('{', '{{').replace('}', '}}')
                # Format as a section in the prompt
                section = f"\n## {doc_name}\n\n{content}"
                doc_sections.append(section)
                logger.info(f"Loaded {doc_name}: {len(content)} characters")
        except Exception as e:
            logger.error(f"Error loading {doc_name}: {str(e)}")
            missing_docs.append(doc_name)

    # If no documents were loaded, return fallback
    if not doc_sections:
        logger.warning("No documentation files could be loaded. Using fallback.")
        return _get_fallback_documentation()

    # If some documents are missing, note it but continue
    if missing_docs:
        logger.warning(f"Partial documentation loaded. Missing: {', '.join(missing_docs)}")
        formatted_docs = "\n# PARTIAL DOCUMENTATION LOADED\n\n"
        formatted_docs += f"**Note**: Some documentation files are missing: {', '.join(missing_docs)}\n\n"
        formatted_docs += "The following documentation has been preloaded. For missing documents, use MCP tools to access them if needed.\n"
        formatted_docs += "\n".join(doc_sections)
    else:
        logger.info("Successfully loaded all documentation files")
        # Combine all sections with a header
        formatted_docs = "\n# PRELOADED DOCUMENTATION\n\nThe following documentation has been preloaded for your reference. Use these documents to craft responses with verbatim language whenever possible.\n" + "\n".join(doc_sections)

    return formatted_docs


def _get_fallback_documentation() -> str:
    """Return empty string when documentation unavailable.

    This should only occur in development/testing environments.
    In production, missing documentation is a configuration error that
    should be addressed immediately.

    Returns:
        Empty string to allow module to load without crashing
    """
    return ""
