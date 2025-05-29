import json
from typing import Optional

from django.conf import settings
from firecrawl import AsyncFirecrawlApp, ScrapeOptions, JsonConfig
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.types import PyHubTextChoices


# Firecrawl format choices
class FormatChoices(PyHubTextChoices):
    MARKDOWN = "markdown"
    HTML = "html"
    RAW_HTML = "rawHtml"
    CONTENT = "content"
    LINKS = "links"
    SCREENSHOT = "screenshot"
    SCREENSHOT_FULL_PAGE = "screenshot@fullPage"
    EXTRACT = "extract"
    JSON = "json"
    CHANGE_TRACKING = "changeTracking"


# Firecrawl action type choices
class ActionTypeChoices(PyHubTextChoices):
    WAIT = "wait"
    CLICK = "click"
    SCREENSHOT = "screenshot"
    WRITE = "write"
    PRESS = "press"
    SCROLL = "scroll"
    SCRAPE = "scrape"
    EXECUTE_JAVASCRIPT = "executeJavascript"


# Firecrawl scroll direction choices
class ScrollDirectionChoices(PyHubTextChoices):
    UP = "up"
    DOWN = "down"


ENABLED_FIRECRAWL_TOOLS = settings.FIRECRAWL_API_KEY is not None


@mcp.tool(enabled=ENABLED_FIRECRAWL_TOOLS)
async def search__firecrawl(
    url: str = Field(
        description="The URL to scrape",
        examples=["https://example.com", "https://python.org"],
    ),
    formats: str = Field(
        default="markdown",
        description="Content formats to extract (default: 'markdown'). comma-separated values",
        examples=["markdown", "html,screenshot", "markdown,links"],
    ),
    only_main_content: bool = Field(
        default=False,
        description="Extract only the main content, filtering out navigation, footers, etc.",
    ),
    include_tags: str = Field(
        default="",
        description="HTML tags to specifically include in extraction (comma-separated values)",
        examples=["article,main", "div.content"],
    ),
    exclude_tags: str = Field(
        default="",
        description="HTML tags to exclude from extraction (comma-separated values)",
        examples=["nav,footer", "div.ads"],
    ),
    wait_for: int = Field(
        default=0,
        description="Time in milliseconds to wait for dynamic content to load",
    ),
    timeout: int = Field(
        default=30000,
        description="Maximum time in milliseconds to wait for the page to load",
    ),
    actions: str = Field(
        default="",
        description="List of actions to perform before scraping",
        examples=[
            "wait(milliseconds=1000)\nclick(selector=button.load-more)\nscroll(direction=down_)",
        ],
    ),
    extract: Optional[JsonConfig] = Field(
        default=None,
        description="Configuration for structured data extraction",
        examples=[
            {
                "schema": {
                    "title": "string",
                    "price": "number",
                    "description": "string",
                },
                "systemPrompt": "Extract product information",
                "prompt": "Extract the product details from this page",
            }
        ],
    ),
    mobile: bool = Field(
        default=False,
        description="Use mobile viewport",
    ),
    skip_tls_verification: bool = Field(
        default=False,
        description="Skip TLS certificate verification",
    ),
    remove_base64_images: bool = Field(
        default=False,
        description="Remove base64 encoded images from output",
    ),
    location: Optional[dict] = Field(
        default=None,
        description="Location settings for scraping",
        examples=[
            {
                "country": "US",
                "languages": ["en"],
            }
        ],
    ),
) -> str:
    """Scrapes a single webpage with advanced options for content extraction.

    This tool provides comprehensive web scraping capabilities with support for:
    - Multiple content formats (markdown, HTML, screenshots, etc.)
    - Dynamic content handling
    - Custom actions (clicking, scrolling, etc.)
    - Structured data extraction
    - Mobile viewport simulation
    - Geolocation settings

    Returns:
        str: A JSON-encoded string containing the scraped content and metadata.
    """
    app = AsyncFirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)

    # Convert comma-separated strings to lists
    format_list = [f.strip() for f in formats.split(",")]
    include_tags_list = [tag.strip() for tag in include_tags.split(",")] if include_tags else []
    exclude_tags_list = [tag.strip() for tag in exclude_tags.split(",")] if exclude_tags else []

    # Parse actions string into list of action dictionaries
    action_list = []
    if actions:
        for action_str in actions.strip().split("\n"):
            if not action_str:
                continue
            action_type = action_str.split("(")[0]
            params_str = action_str.split("(")[1].rstrip(")")
            params = {}
            for param in params_str.split(","):
                if "=" in param:
                    key, value = param.split("=")
                    params[key.strip()] = value.strip()
            action_list.append({"type": action_type, **params})

    scrape_options = ScrapeOptions(
        formats=format_list or None,
        onlyMainContent=only_main_content,
        includeTags=include_tags_list or None,
        excludeTags=exclude_tags_list,
        waitFor=wait_for,
        timeout=timeout,
        mobile=mobile,
        skipTlsVerification=skip_tls_verification,
        removeBase64Images=remove_base64_images,
        location=location,
    )

    result = await app.scrape_url(
        url,
        scrape_options=scrape_options,
        actions=action_list or None,
        extract=extract,
    )

    formatted_result = {
        "url": url,
        "content": result.get("content", {}),
        "metadata": result.get("metadata", {}),
        "screenshots": result.get("screenshots", []),
        "links": result.get("links", []),
    }
    return json.dumps(formatted_result, ensure_ascii=False)
