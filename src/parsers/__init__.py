"""
Parser Registry

Simplified registry of parsers for different website types.
"""

from typing import Dict, Any
from src.parsers.base_parser import BaseParser

# Import all parser classes
from src.parsers.sbi_parser import SBIParser
from src.parsers.pnb_parser import PNBParser

# Map of website types to parser classes
_PARSER_REGISTRY = {
    "SBI": SBIParser,
    "PNB": PNBParser
}

def get_parser_for_website(website_config: Dict[str, Any]) -> BaseParser:
    """
    Get the appropriate parser for a website based on its type.

    Args:
        website_config: Website configuration dictionary

    Returns:
        Parser instance for the website

    Raises:
        ValueError: If website type is not supported
    """
    website_type = website_config.get('type')

    if not website_type:
        raise ValueError(f"Website configuration missing 'type': {website_config}")

    parser_class = _PARSER_REGISTRY.get(website_type)

    if not parser_class:
        raise ValueError(f"No parser available for website type: {website_type}")

    return parser_class(website_config)
