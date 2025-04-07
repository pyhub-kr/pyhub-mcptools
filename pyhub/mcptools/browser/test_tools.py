import pytest
from pytest_httpx import HTTPXMock

from pyhub.mcptools.browser.tools import get_webpage_metadata


@pytest.mark.asyncio
async def test_get_webpage_metadata(httpx_mock: HTTPXMock):
    # Mock the HTTP response with sample HTML
    mock_html = """
    <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="This is a test page">
            <meta property="og:title" content="OG Test Title">
            <meta property="og:description" content="OG test description">
        </head>
        <body>
            <h1>Test Page</h1>
        </body>
    </html>
    """
    httpx_mock.add_response(text=mock_html)

    # Call the function
    metadata = await get_webpage_metadata("https://www.example.com")

    # Assert the metadata was correctly extracted
    assert metadata["title"] == "Test Page"
    assert metadata["meta"]["description"] == "This is a test page"
    assert metadata["og"]["og:title"] == "OG Test Title"
    assert metadata["og"]["og:description"] == "OG test description"
