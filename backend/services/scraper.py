import httpx
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from typing import List, Dict, Any

async def scrape_reuters_news() -> List[Dict[str, Any]]:
    """
    Scrapes reuters.com for latest geopolitical and macro news headlines.
    """
    url = "https://www.reuters.com/world/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    news_items = []
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                # Find news headings (Reuters uses specific data-testid or class names)
                headings = soup.find_all(["h3", "a"], attrs={"data-testid": "Heading"})
                if not headings:
                    # Fallback to general link/heading search
                    headings = soup.find_all("a", class_=lambda x: x and "Link" in x and "Heading" in x)
                
                for heading in headings[:5]:
                    text = heading.get_text().strip()
                    link = heading.get("href", "")
                    if text and len(text) > 15:
                        news_items.append({
                            "title": text,
                            "url": f"https://www.reuters.com{link}" if link.startswith("/") else link,
                            "source": "Reuters Scraper"
                        })
    except Exception as e:
        print(f"[Scraper] Failed to scrape Reuters: {e}")
    return news_items

async def scrape_bbc_news() -> List[Dict[str, Any]]:
    """
    Scrapes bbc.com/news for latest global news headlines.
    """
    url = "https://www.bbc.com/news"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    news_items = []
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                # BBC uses h2/h3 for headlines
                headings = soup.find_all(["h2", "h3"])
                for heading in headings[:8]:
                    text = heading.get_text().strip()
                    parent_a = heading.find_parent("a") or heading.find("a")
                    link = parent_a.get("href", "") if parent_a else ""
                    if text and len(text) > 15:
                        news_items.append({
                            "title": text,
                            "url": f"https://www.bbc.com{link}" if link.startswith("/") else link,
                            "source": "BBC Scraper"
                        })
    except Exception as e:
        print(f"[Scraper] Failed to scrape BBC: {e}")
    return news_items

async def fetch_forexfactory_calendar() -> List[Dict[str, Any]]:
    """
    Fetches and parses the official ForexFactory weekly calendar XML feed.
    This is highly accurate and free.
    """
    url = "https://www.forexfactory.com/ffcal_week_this.xml"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    news_items = []
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for event in root.findall("event"):
                    title = event.find("title").text if event.find("title") is not None else ""
                    country = event.find("country").text if event.find("country") is not None else ""
                    impact = event.find("impact").text if event.find("impact") is not None else ""
                    
                    # Filter high impact (Red Folder) or medium impact events
                    if impact in ["High", "Medium"] and country in ["USD", "EUR", "GBP"]:
                        news_items.append({
                            "title": f"FF CALENDAR: {country} - {title} ({impact} Impact)",
                            "url": "https://www.forexfactory.com/calendar",
                            "source": "ForexFactory Calendar"
                        })
    except Exception as e:
        print(f"[Scraper] Failed to fetch ForexFactory calendar: {e}")
    return news_items

async def fetch_crypto_panic_news() -> List[Dict[str, Any]]:
    """
    Fetches latest crypto news from CryptoPanic's public RSS feed.
    Highly accurate, real-time, and free.
    Uses BeautifulSoup to parse HTML/XML safely.
    """
    url = "https://cryptopanic.com/news/rss/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    news_items = []
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                # Use html.parser or xml parser in BeautifulSoup to handle malformed tags safely
                soup = BeautifulSoup(response.content, "xml")
                items = soup.find_all("item")
                for item in items:
                    title_tag = item.find("title")
                    link_tag = item.find("link")
                    title = title_tag.get_text().strip() if title_tag else ""
                    link = link_tag.get_text().strip() if link_tag else ""
                    if title:
                        news_items.append({
                            "title": title,
                            "url": link,
                            "source": "CryptoPanic RSS"
                        })
    except Exception as e:
        print(f"[Scraper] Failed to fetch CryptoPanic news: {e}")
    return news_items
