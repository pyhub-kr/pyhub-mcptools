"""
Images automation
"""

import traceback
from typing import Optional, Union

from mcp.server.fastmcp import Image as FastMCPImage
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.images.generators import ImageGenerator
from pyhub.mcptools.images.types import ImageGeneratorVendor
from pyhub.mcptools.images.utils import convert_base64_image


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


@mcp.tool()
async def images_convert(
    image_base64_data: str = Field(description="base64 인코딩된 이미지 데이터 (SVG, PNG, JPEG, WebP, GIF 등)"),
    format: Optional[str] = Field(default="PNG", description="출력 이미지 포맷 (PNG, JPEG, WEBP, BMP, TIFF 등)"),
    width: Optional[int] = Field(default=None, description="출력 이미지 너비 (픽셀)"),
    height: Optional[int] = Field(default=None, description="출력 이미지 높이 (픽셀)"),
    maintain_aspect_ratio: bool = Field(default=True, description="가로세로 비율 유지 여부"),
    crop_box: Optional[list[int]] = Field(default=None, description="크롭 영역 [left, top, right, bottom] 좌표"),
    thumbnail_size: Optional[list[int]] = Field(
        default=None, description="썸네일 크기 [width, height]. 설정하면 썸네일 모드로 동작"
    ),
    quality: int = Field(default=95, description="JPEG 압축 품질 (1-100)"),
) -> FastMCPImage:
    """base64 인코딩된 이미지 데이터를 다양한 형식으로 변환하고 처리합니다.

    지원 기능:
        - 다양한 입력 형식: SVG, PNG, JPEG, WebP, GIF, BMP, TIFF
        - 자동 형식 감지 (magic bytes 기반)
        - 출력 형식 변환 (PNG, JPEG, WebP 등)
        - 이미지 크기 조정 (가로세로 비율 유지 옵션)
        - 이미지 크롭
        - 썸네일 생성
        - data URI scheme 지원 (data:image/png;base64,...)

    예시:
        >>> images_convert("PD94bWwgdmVyc2lvbj0i...")  # SVG base64를 PNG로 변환
        >>> images_convert("iVBORw0KGgoAAAA...", format="JPEG")  # PNG base64를 JPEG로 변환
        >>> images_convert("data:image/png;base64,iVBORw0KGgo...", width=200)  # data URI로 크기 조정
        >>> images_convert("iVBORw0KGgoAAAA...", thumbnail_size=[100, 100])  # 썸네일 생성
        >>> images_convert("iVBORw0KGgoAAAA...", crop_box=[10, 10, 200, 200])  # 크롭 처리
    """
    return await convert_base64_image(
        image_base64_data=image_base64_data,
        format=format,
        width=width,
        height=height,
        maintain_aspect_ratio=maintain_aspect_ratio,
        crop_box=crop_box,
        thumbnail_size=thumbnail_size,
        quality=quality,
    )
