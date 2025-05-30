import base64
import io
from typing import Optional

import httpx
from mcp.server.fastmcp import Image as FastMCPImage
from PIL import Image as PILImage


async def fetch_image(url: str) -> PILImage:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return PILImage.open(io.BytesIO(response.content))


def detect_image_format(data: bytes) -> str:
    """Detect image format from binary data using magic bytes"""
    # SVG detection (text-based)
    try:
        text = data.decode("utf-8", errors="ignore").strip()
        if text.startswith("<?xml") and "<svg" in text or text.startswith("<svg"):
            return "svg"
    except:
        pass

    # Binary format detection using magic bytes
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    elif data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    elif data.startswith(b"RIFF") and b"WEBP" in data[:12]:
        return "webp"
    elif data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    elif data.startswith(b"BM"):
        return "bmp"
    elif data.startswith(b"II*\x00") or data.startswith(b"MM\x00*"):
        return "tiff"
    else:
        return "unknown"


async def convert_base64_image(
    image_base64_data: str,
    format: Optional[str] = "PNG",
    width: Optional[int] = None,
    height: Optional[int] = None,
    maintain_aspect_ratio: bool = True,
    crop_box: Optional[list[int]] = None,
    thumbnail_size: Optional[list[int]] = None,
    quality: int = 95,
) -> FastMCPImage:
    """Convert base64 encoded image data to another format

    Args:
        image_base64_data: Base64 encoded image data
        format: Output format (PNG, JPEG, WEBP, etc.)
        width: Output width in pixels
        height: Output height in pixels
        maintain_aspect_ratio: Whether to maintain aspect ratio when resizing
        crop_box: Crop coordinates [left, top, right, bottom]
        thumbnail_size: Thumbnail size [width, height]
        quality: JPEG quality (1-100)

    Returns:
        FastMCPImage object containing the converted image

    Raises:
        ValueError: If image data is invalid or parameters are incorrect
        ImportError: If cairosvg is not installed for SVG processing
    """
    try:
        # Base64 디코딩
        try:
            # data:image/... URI scheme 처리
            if image_base64_data.startswith("data:"):
                # data:image/png;base64,iVBORw0KGgo... 형태에서 base64 부분만 추출
                base64_part = image_base64_data.split(",", 1)[1] if "," in image_base64_data else image_base64_data
            else:
                base64_part = image_base64_data

            image_data = base64.b64decode(base64_part)
        except Exception as e:
            raise ValueError(f"Base64 디코딩 실패: {e}")

        # 이미지 형식 자동 감지
        detected_format = detect_image_format(image_data)

        # SVG 처리
        if detected_format == "svg":
            try:
                import cairosvg

                png_data = cairosvg.svg2png(bytestring=image_data)
                img = PILImage.open(io.BytesIO(png_data))
            except ImportError:
                raise ImportError("SVG 변환을 위해 cairosvg 패키지가 필요합니다. pip install cairosvg")
            except Exception as e:
                raise ValueError(f"SVG 처리 중 오류: {e}")
        else:
            # 일반 이미지 파일 처리
            try:
                img = PILImage.open(io.BytesIO(image_data))
            except Exception as e:
                raise ValueError(f"이미지 파일 처리 중 오류: {e}")

        # RGBA 모드로 변환 (투명도 지원)
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # 크롭 처리
        if crop_box is not None:
            if isinstance(crop_box, (list, tuple)) and len(crop_box) == 4:
                img = img.crop(crop_box)
            else:
                raise ValueError("crop_box는 [left, top, right, bottom] 형태의 4개 값이어야 합니다")

        # 썸네일 모드
        if thumbnail_size is not None:
            if isinstance(thumbnail_size, (list, tuple)) and len(thumbnail_size) == 2:
                img.thumbnail(thumbnail_size, PILImage.Resampling.LANCZOS)
            else:
                raise ValueError("thumbnail_size는 [width, height] 형태의 2개 값이어야 합니다")

        # 크기 조정
        elif width or height:
            original_width, original_height = img.size

            if maintain_aspect_ratio:
                if width and height:
                    # 둘 다 지정된 경우 비율 유지하며 작은 쪽에 맞춤
                    ratio = min(width / original_width, height / original_height)
                    new_width = int(original_width * ratio)
                    new_height = int(original_height * ratio)
                elif width:
                    # 너비만 지정된 경우
                    ratio = width / original_width
                    new_width = width
                    new_height = int(original_height * ratio)
                else:
                    # 높이만 지정된 경우
                    ratio = height / original_height
                    new_width = int(original_width * ratio)
                    new_height = height
            else:
                # 비율 무시하고 직접 크기 지정
                new_width = width or original_width
                new_height = height or original_height

            img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)

        # 포맷 결정
        if format is None:
            format = "PNG"

        format = format.upper()

        # JPEG의 경우 RGB로 변환 (투명도 제거)
        if format == "JPEG" and img.mode == "RGBA":
            # 흰색 배경으로 합성
            background = PILImage.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])  # 알파 채널을 마스크로 사용
            img = background

        # MCP Image로 반환
        buffer = io.BytesIO()
        save_kwargs = {}
        if format == "JPEG":
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True

        img.save(buffer, format=format, **save_kwargs)
        buffer.seek(0)

        return FastMCPImage(data=buffer.getvalue(), format=format.lower())

    except Exception as e:
        raise ValueError(f"이미지 변환 중 오류가 발생했습니다: {e}")
