import pytest
from unittest.mock import patch, AsyncMock
from app.services.scraper import WebScraper
from app.core.errors import ScraperError


@pytest.mark.asyncio
async def test_scraper_fetch_and_extract_mocked():
    scraper = WebScraper()
    mock_html = """
    <html>
        <head><title>Turium AI Innovation</title></head>
        <body>
            <h1>Turium Knowledge Inbox</h1>
            <p>Turium builds modern AI platforms for enterprises with seamless RAG pipelines.</p>
        </body>
    </html>
    """

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_response.text = mock_html
    mock_response.url = "https://turium.ai/blog/rag-pipeline"

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await scraper.fetch_and_extract("https://turium.ai/blog/rag-pipeline")
        assert result["title"] == "Turium AI Innovation"
        assert "Turium Knowledge Inbox" in result["content"]
        assert result["word_count"] > 5
        assert result["url"] == "https://turium.ai/blog/rag-pipeline"


@pytest.mark.asyncio
async def test_scraper_http_error_handling():
    scraper = WebScraper()
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.headers = {"content-type": "text/html"}

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        with pytest.raises(ScraperError) as exc_info:
            await scraper.fetch_and_extract("https://example.com/not-found")
        assert "Received HTTP 404" in str(exc_info.value.message)
