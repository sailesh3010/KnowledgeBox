import re
import httpx
from typing import Dict, Any, Tuple
from app.core.config import get_settings
from app.core.logging import logger
from app.core.errors import ScraperError
import lxml.html


class WebScraper:
    """Server-side web page scraper and article text extractor."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "TuriumKnowledgeInbox/1.0 (Personal AI Knowledge Inbox; contact: info@turium.ai) "
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
    }

    def __init__(self):
        self.settings = get_settings()

    async def fetch_and_extract(self, url: str) -> Dict[str, Any]:
        """
        Fetch HTML content from url and extract clean readable text and metadata.
        Returns:
            {
                "url": str,
                "title": str,
                "content": str,
                "char_count": int,
                "word_count": int,
                "status_code": int
            }
        """
        logger.info(f"Fetching URL: {url}")

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.SCRAPE_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=self.DEFAULT_HEADERS,
                verify=True,
            ) as client:
                response = await client.get(url)

                if response.status_code >= 400:
                    raise ScraperError(
                        message=f"Received HTTP {response.status_code} while fetching '{url}'.",
                        details={"status_code": response.status_code, "url": url},
                    )

                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "application/xhtml" not in content_type and "text/plain" not in content_type:
                    raise ScraperError(
                        message=f"URL does not return HTML or plain text (Content-Type: '{content_type}').",
                        details={"content_type": content_type, "url": url},
                    )

                html_text = response.text
                if len(html_text) > self.settings.MAX_CONTENT_CHARS:
                    html_text = html_text[:self.settings.MAX_CONTENT_CHARS]

        except httpx.TimeoutException:
            raise ScraperError(
                message=f"Request to '{url}' timed out after {self.settings.SCRAPE_TIMEOUT_SECONDS}s.",
                details={"url": url, "timeout": self.settings.SCRAPE_TIMEOUT_SECONDS},
            )
        except httpx.RequestError as e:
            raise ScraperError(
                message=f"Network error while connecting to '{url}': {str(e)}",
                details={"url": url, "error": str(e)},
            )
        except ScraperError:
            raise
        except Exception as e:
            raise ScraperError(
                message=f"Unexpected error fetching '{url}': {str(e)}",
                details={"url": url, "error": str(e)},
            )

        title, cleaned_text = self._clean_html(html_text, fallback_url=url)

        if not cleaned_text or len(cleaned_text.strip()) < 10:
            raise ScraperError(
                message=f"No readable text could be extracted from '{url}'. The page may require JavaScript or authentication.",
                details={"url": url},
            )

        return {
            "url": str(response.url),
            "title": title or url,
            "content": cleaned_text,
            "char_count": len(cleaned_text),
            "word_count": len(cleaned_text.split()),
            "status_code": response.status_code,
        }

    def _clean_html(self, html_content: str, fallback_url: str) -> Tuple[str, str]:
        """Extract title and strip tags to produce clean article prose."""
        try:
            doc = lxml.html.fromstring(html_content)
        except Exception:
            # Fallback regex extraction if parsing fails
            clean_text = re.sub(r"<[^>]+>", " ", html_content)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            return fallback_url, clean_text

        # Extract title: check <title>, <meta property="og:title">, or <h1>
        title = ""
        og_title = doc.xpath('//meta[@property="og:title"]/@content')
        if og_title and og_title[0].strip():
            title = og_title[0].strip()
        else:
            title_tags = doc.xpath('//title/text()')
            if title_tags and title_tags[0].strip():
                title = title_tags[0].strip()
            else:
                h1_tags = doc.xpath('//h1/text()')
                if h1_tags and h1_tags[0].strip():
                    title = h1_tags[0].strip()

        # Remove boilerplate and noise tags
        tags_to_drop = [
            "script", "style", "noscript", "nav", "header", "footer",
            "aside", "form", "svg", "button", "iframe", "figure"
        ]
        for tag in tags_to_drop:
            for el in doc.xpath(f"//{tag}"):
                el.drop_tree()

        # Extract textual content from remaining elements
        raw_text = doc.text_content()

        # Normalize whitespace while preserving paragraph separation
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        cleaned_text = "\n\n".join(lines)

        return title or fallback_url, cleaned_text


scraper = WebScraper()
