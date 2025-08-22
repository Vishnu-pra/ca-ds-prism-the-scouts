"""
Parser Registry

Simplified registry of parsers for different website types.
"""

from typing import Dict, Any

# Import all parser classes
from src.crawler.sbi_crawler import main as SBI_crawler
from src.crawler.canara_crawler import main as Canara_crawler
from src.crawler.idbi_crawler import main as IDBI_crawler
from src.crawler.uco_crawler import main as UCO_crawler

# Map of website types to parser classes
_PARSER_REGISTRY = {
    "SBI": SBI_crawler,
    "CANARA": Canara_crawler,
    "IDBI": IDBI_crawler,
    "UCO": UCO_crawler
}

def get_crawler_for_website(website_type: str):
    """
    Get the appropriate parser for a website based on its type.

    Args:
        website_config: Website configuration dictionary

    Returns:
        Parser instance for the website

    Raises:
        ValueError: If website type is not supported
    """
    if not website_type:
        raise ValueError(f"Website configuration missing 'type': {website_config}")

    crawler_function = _PARSER_REGISTRY.get(website_type)

    if not crawler_function:
        raise ValueError(f"No parser available for website type: {website_type}")

    return crawler_function
