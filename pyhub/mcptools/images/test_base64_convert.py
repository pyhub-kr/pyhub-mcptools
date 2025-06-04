"""
Test for base64 image conversion functionality
"""

import base64
import os
import tempfile

import pytest
from PIL import Image as PILImage

from pyhub.mcptools.images.utils import convert_base64_image, detect_image_format


class TestBase64Convert:

    def setup_method(self):
        """Create test image data"""
        self.temp_dir = tempfile.mkdtemp()

        # Create simple test images and convert to base64
        # PNG image
        png_img = PILImage.new("RGBA", (50, 50), (255, 0, 0, 255))  # Red square
        png_path = os.path.join(self.temp_dir, "test.png")
        png_img.save(png_path, "PNG")

        with open(png_path, "rb") as f:
            self.png_base64 = base64.b64encode(f.read()).decode("utf-8")

        # JPEG image
        jpg_img = PILImage.new("RGB", (60, 40), (0, 255, 0))  # Green rectangle
        jpg_path = os.path.join(self.temp_dir, "test.jpg")
        jpg_img.save(jpg_path, "JPEG")

        with open(jpg_path, "rb") as f:
            self.jpg_base64 = base64.b64encode(f.read()).decode("utf-8")

        # SVG content
        self.svg_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
  <rect width="100" height="100" fill="#3498db"/>
  <circle cx="50" cy="50" r="25" fill="#e74c3c"/>
</svg>"""
        self.svg_base64 = base64.b64encode(self.svg_content.encode("utf-8")).decode("utf-8")

    def test_detect_image_format(self):
        """Test image format detection"""
        # Test PNG detection
        png_data = base64.b64decode(self.png_base64)
        assert detect_image_format(png_data) == "png"

        # Test JPEG detection
        jpg_data = base64.b64decode(self.jpg_base64)
        assert detect_image_format(jpg_data) == "jpeg"

        # Test SVG detection
        svg_data = base64.b64decode(self.svg_base64)
        assert detect_image_format(svg_data) == "svg"

    @pytest.mark.asyncio
    async def test_png_base64_conversion(self):
        """Test PNG base64 conversion"""
        result = await convert_base64_image(self.png_base64)

        # Should return FastMCPImage
        assert hasattr(result, "data")
        assert result.data is not None
        assert len(result.data) > 0

    @pytest.mark.asyncio
    async def test_jpg_base64_conversion(self):
        """Test JPEG base64 conversion"""
        result = await convert_base64_image(self.jpg_base64, format="PNG")

        # Should return FastMCPImage
        assert hasattr(result, "data")
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_svg_base64_conversion_error(self):
        """Test SVG base64 conversion raises error"""
        with pytest.raises(ValueError, match="SVG 형식은 지원되지 않습니다"):
            await convert_base64_image(self.svg_base64)

    @pytest.mark.asyncio
    async def test_data_uri_scheme(self):
        """Test data URI scheme support"""
        data_uri = f"data:image/png;base64,{self.png_base64}"
        result = await convert_base64_image(data_uri)

        # Should return FastMCPImage
        assert hasattr(result, "data")
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_format_conversion(self):
        """Test format conversion PNG to JPEG"""
        result = await convert_base64_image(self.png_base64, format="JPEG")

        # Should return FastMCPImage
        assert hasattr(result, "data")
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_resize_functionality(self):
        """Test image resizing"""
        result = await convert_base64_image(self.png_base64, width=25, height=25)

        # Should return FastMCPImage
        assert hasattr(result, "data")

    @pytest.mark.asyncio
    async def test_thumbnail_functionality(self):
        """Test thumbnail generation"""
        result = await convert_base64_image(self.jpg_base64, thumbnail_size=[30, 30])

        # Should return FastMCPImage
        assert hasattr(result, "data")

    @pytest.mark.asyncio
    async def test_crop_functionality(self):
        """Test cropping functionality"""
        result = await convert_base64_image(self.png_base64, crop_box=[10, 10, 40, 40])

        # Should return FastMCPImage
        assert hasattr(result, "data")

    @pytest.mark.asyncio
    async def test_invalid_base64(self):
        """Test invalid base64 input"""
        with pytest.raises(ValueError, match="Base64 디코딩 실패"):
            await convert_base64_image("invalid_base64_data!!!")

    @pytest.mark.asyncio
    async def test_invalid_crop_box(self):
        """Test invalid crop box"""
        with pytest.raises(ValueError, match="crop_box는"):
            await convert_base64_image(self.png_base64, crop_box=[10, 20])  # Invalid: only 2 values

    @pytest.mark.asyncio
    async def test_invalid_thumbnail_size(self):
        """Test invalid thumbnail size"""
        with pytest.raises(ValueError, match="thumbnail_size는"):
            await convert_base64_image(self.png_base64, thumbnail_size=[100])  # Invalid: only 1 value

    @pytest.mark.asyncio
    async def test_quality_setting(self):
        """Test JPEG quality setting"""
        result = await convert_base64_image(self.png_base64, format="JPEG", quality=50)

        # Should return FastMCPImage
        assert hasattr(result, "data")
        assert result.data is not None

    def teardown_method(self):
        """Clean up test files"""
        import shutil

        shutil.rmtree(self.temp_dir)
