import asyncio
import sys
from typing import Dict, Any
from logger_config import setup_logger

# Fallback imports
import requests
from bs4 import BeautifulSoup

logger = setup_logger("crawler_agent")

# Handle Windows encoding issues for logs
if sys.platform == 'win32':
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    # In 0.7.x, names might have slightly changed
    CRAWL4AI_AVAILABLE = True
except Exception as e:
    logger.warning(f"crawl4ai import failed: {e}. Falling back to basic requests/BeautifulSoup crawler.")
    CRAWL4AI_AVAILABLE = False

class CrawlerAgent:
    """
    Advanced Crawler Agent that uses Crawl4AI for high-quality web scraping.
    Handles JavaScript rendering and provides clean Markdown output.
    """
    
    def __init__(self, use_javascript: bool = True):
        self.use_javascript = use_javascript
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def _crawl_advanced(self, url: str) -> str:
        """Asynchronous crawl using Crawl4AI."""
        browser_config = BrowserConfig(
            headless=True,
            java_script_enabled=self.use_javascript,
            headers=self.headers
        )
        
        # In 0.7.x, run_config handles many options
        run_config = CrawlerRunConfig(
            cache_mode="bypass",
            # Default options are good for general scraping
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            
            if result.success:
                # return the best available markdown
                return result.markdown.raw_markdown if result.markdown else ""
            else:
                raise Exception(f"Crawl4AI failed: {result.error_message}")

    def scrape(self, url: str, max_chars: int = 15000) -> str:
        """
        Synchronous wrapper for scraping that chooses the best available method.
        """
        logger.info(f"Crawl started for: {url}")
        print(f"   [CRAWLER] 🌐 Initializing scrape for: {url}")
        
        if CRAWL4AI_AVAILABLE:
            try:
                print("   [CRAWLER] 🚀 Using Advanced Mode (Crawl4AI + JS Rendering)...")
                # Create a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                content = loop.run_until_complete(self._crawl_advanced(url))
                loop.close()
                
                logger.info(f"Crawl4AI successfully scraped content from {url}")
                print(f"   [CRAWLER] ✅ Success! Extracted {len(content)} characters of Markdown content.")
                return f"--- Advanced Content from {url} ---\n\n{content[:max_chars]}\n--- End of Content ---"
            
            except Exception as e:
                logger.warning(f"Crawl4AI failed, falling back to basic scraper: {e}")
                print(f"   [CRAWLER] ⚠️ Advanced mode failed: {e}")
        
        # Fallback to Basic Scraper
        print("   [CRAWLER] 🐢 Falling back to Basic Scraper (Static HTML)...")
        return self._scrape_basic(url, max_chars)

    def _scrape_basic(self, url: str, max_chars: int) -> str:
        """Fallback scraper using requests and BeautifulSoup."""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Junk removal
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()

            text = soup.get_text(separator='\n')
            lines = (line.strip() for line in text.splitlines())
            text = '\n'.join(line for line in lines if line)
            
            content = text[:max_chars]
            return f"--- Basic Scraped Content (Fallback) from {url} ---\n\n{content}\n--- End of Content ---"
            
        except Exception as e:
            logger.error(f"Basic scraping error: {e}")
            return f"Error scraping {url}: {str(e)}"

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Simple metadata extraction."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'lxml')
            return {
                "title": soup.title.string if soup.title else "No title",
                "url": url
            }
        except Exception:
            return {"url": url}
