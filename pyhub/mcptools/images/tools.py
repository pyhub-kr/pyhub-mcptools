"""
Images automation
"""

import traceback
from typing import Union

from mcp.server.fastmcp import Image as FastMCPImage
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.images.generators import ImageGenerator
from pyhub.mcptools.images.types import ImageGeneratorVendor


@mcp.tool(experimental=True)
async def images_generate(
    query: str = Field(
        description="Text description of the image to generate.",
        examples=[
            "A beautiful sunset over mountains",
            "A cute cartoon cat playing with yarn",
            "An abstract painting with vibrant colors",
        ],
    ),
    vendor: ImageGeneratorVendor = Field(
        description="The AI image generation service provider to use.",
        examples=[
            ImageGeneratorVendor.UNSPLASH,
            ImageGeneratorVendor.TOGETHER_AI,
        ],
    ),
    width: int = Field(
        default=1024,
        description="Width of the generated image in pixels.",
        examples=[512, 1024, 2048],
    ),
    height: int = Field(
        default=1024,
        description="Height of the generated image in pixels.",
        examples=[512, 1024, 2048],
    ),
) -> Union[str, FastMCPImage]:
    """Generate an AI-created image based on a text description.

    Uses various AI image generation services to create images from text descriptions.
    Supports multiple vendors and customizable image dimensions.

    Generation Rules:
        - Image dimensions must be supported by the selected vendor
        - Query should be descriptive and clear for best results
        - Some vendors may have specific formatting requirements for queries
        - Generated images will be returned in their original format

    Error Handling:
        - Returns error message as string if generation fails
        - Returns traceback as string for unexpected errors
        - Validates image dimensions against vendor limitations

    Returns:
        Union[str, FastMCPImage]: Either a FastMCPImage object containing the generated image,
                                 or an error message as string if generation fails.

    Examples:
        >>> images_generate("A serene mountain landscape at sunset")  # Basic usage
        >>> images_generate("A futuristic city", vendor=ImageGeneratorVendor.UNSPLASH)  # Specific vendor
        >>> images_generate("A colorful bird", width=512, height=512)  # Custom size
        >>> images_generate("Abstract art", vendor=ImageGeneratorVendor.TOGETHER_AI, width=1024, height=768)
    """

    try:
        pil_image = await ImageGenerator.run(vendor, query=query, width=width, height=height)
        return FastMCPImage(data=pil_image.tobytes(), format=pil_image.format)
    except AssertionError as e:
        return f"Error: {e}"
    except:  # noqa
        return traceback.format_exc()


# @mcp.tool(experimental=True)
# def images_add_text() -> str:
#     pass
