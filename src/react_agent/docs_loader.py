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
        Formatted string containing all documentation content
        
    Raises:
        FileNotFoundError: If docs directory or required files don't exist
    """
    # Determine docs directory
    if docs_dir is None:
        # Default to docs/ directory relative to project root
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        docs_dir = project_root / "docs"
    else:
        docs_dir = Path(docs_dir)
    
    if not docs_dir.exists():
        raise FileNotFoundError(f"Documentation directory not found: {docs_dir}")
    
    logger.info(f"Loading documentation from: {docs_dir}")
    
    # Load each required document
    required_docs = ["blueprint.md", "faq.md", "samples.md"]
    doc_sections = []
    
    for doc_name in required_docs:
        doc_path = docs_dir / doc_name
        if not doc_path.exists():
            raise FileNotFoundError(f"Required documentation file not found: {doc_path}")
        
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
            raise
    
    logger.info("Successfully loaded all documentation files")
    
    # Combine all sections with a header
    formatted_docs = "\n# PRELOADED DOCUMENTATION\n\nThe following documentation has been preloaded for your reference. Use these documents to craft responses with verbatim language whenever possible.\n" + "\n".join(doc_sections)
    
    return formatted_docs
