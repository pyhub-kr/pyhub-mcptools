"""
Browser automation
"""

import httpx
from bs4 import BeautifulSoup
from pydantic import Field

from pyhub.mcptools import mcp


@mcp.tool(experimental=True)
async def get_webpage_metadata(
    url: str = Field(description="webpage url"),
) -> dict:
    """Get metadata in a webpage"""

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    metadata = {"title": soup.title.text if soup.title else None, "meta": {}}

    # 메타 태그 정보 추출
    for meta in soup.find_all("meta"):
        name = meta.get("name") or meta.get("property")
        if name:
            content = meta.get("content")
            metadata["meta"][name] = content

    # Open Graph 태그 추출
    og_tags = {}
    for meta in soup.find_all("meta", property=lambda x: x and x.startswith("og:")):
        og_tags[meta["property"]] = meta.get("content")

    if og_tags:
        metadata["og"] = og_tags

    return metadata
