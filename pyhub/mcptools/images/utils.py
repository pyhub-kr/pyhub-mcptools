from io import BytesIO

import httpx
from PIL import Image as PILImage


async def fetch_image(url: str) -> PILImage:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return PILImage.open(BytesIO(response.content))
