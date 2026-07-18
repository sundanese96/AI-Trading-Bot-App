import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import json
import time
from pathlib import Path
from backend.config import VERIFY_SSL

import asyncio
import aiofiles

CACHE_FILE = Path(__file__).parent.parent / "scraped_cache.json"
CACHE_DURATION = 300  # 5 minutes in seconds
_cache_lock = asyncio.Lock()

async def _read_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            async with aiofiles.open(CACHE_FILE, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except Exception:
            return {}
    return {}

async def _write_cache(cache_data: dict):
    try:
        async with aiofiles.open(CACHE_FILE, "w", encoding="utf-8") as f:
            await f.write(json.dumps(cache_data, indent=2))
    except Exception as e:
        print(f"[Scraper Cache] Failed to write cache: {e}")

async def get_cached_data(key: str) -> Any:
    async with _cache_lock:
        cache = await _read_cache()
        if key in cache:
            entry = cache[key]
            if time.time() - entry.get("timestamp", 0) < CACHE_DURATION:
                return entry.get("data")
        return None

async def set_cached_data(key: str, data: Any):
    async with _cache_lock:
        cache = await _read_cache()
        cache[key] = {
            "timestamp": time.time(),
            "data": data
        }
        await _write_cache(cache)

async def scrape_reuters_news() -> List[Dict[str, Any]]:
    """
    Scrapes reuters.com for latest geopolitical and macro news headlines.
    """
    cached = await get_cached_data("reuters")
    if cached is not None:
        print("[Scraper Cache] Returning cached Reuters news")
        return cached

    url = "https://www.reuters.com/world/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    news_items = []
    try:
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                # Find news headings using robust CSS selectors
                headings = soup.select("h3[data-testid='Heading'], a[data-testid='Heading']")
                if not headings:
                    # Fallback to general link/heading search within main content areas
                    headings = soup.select("div[class*='story-content'] a, h3 a, a[class*='link']")
                
                for heading in headings[:5]:
                    text = heading.get_text().strip()
                    # If heading is an a tag, it has href. If h3, find the closest a tag parent or child
                    link_elem = heading if heading.name == 'a' else (heading.find_parent('a') or heading.find('a'))
                    link = link_elem.get("href", "") if link_elem else ""
                    if text and len(text) > 15:
                        news_items.append({
                            "title": text,
                            "url": f"https://www.reuters.com{link}" if link.startswith("/") else link,
                            "source": "Reuters Scraper"
                        })
        await set_cached_data("reuters", news_items)
    except Exception as e:
        print(f"[Scraper] Failed to scrape Reuters: {e}")
    return news_items

async def scrape_bbc_news() -> List[Dict[str, Any]]:
    """
    Scrapes bbc.com/news for latest global news headlines.
    """
    cached = await get_cached_data("bbc")
    if cached is not None:
        print("[Scraper Cache] Returning cached BBC news")
        return cached

    url = "https://www.bbc.com/news"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    news_items = []
    try:
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                # BBC uses specific test ids or card classes for main headlines
                headings = soup.select("[data-testid='card-headline']")
                if not headings:
                    headings = soup.find_all(["h2", "h3"], class_=lambda x: x and "card" in x.lower())
                    
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
        await set_cached_data("bbc", news_items)
    except Exception as e:
        print(f"[Scraper] Failed to scrape BBC: {e}")
    return news_items

async def fetch_forexfactory_calendar() -> List[Dict[str, Any]]:
    """
    Fetches and parses the official ForexFactory weekly calendar JSON feed.
    This is highly accurate, free, and bypasses Cloudflare 403 blocks.
    """
    cached = await get_cached_data("forexfactory")
    if cached is not None:
        print("[Scraper Cache] Returning cached ForexFactory calendar")
        return cached

    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    news_items = []
    try:
        events = []
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                try:
                    events = response.json()
                    if not isinstance(events, list):
                        raise ValueError("Not a list")
                except Exception:
                    events = []
            else:
                events = []
        
        # Fallback if rate limited or failed
        if not events:
            print("[Scraper] ForexFactory rate-limited or failed. Returning empty list.")
            events = []

        for event in events:
            title = event.get("title", "")
            country = event.get("country", "")
            impact = event.get("impact", "")
            forecast = event.get("forecast", "")
            previous = event.get("previous", "")
            if impact in ["High", "Medium"] and country in ["USD", "EUR", "GBP"]:
                news_items.append({
                    "title": f"FF CALENDAR: {country} - {title} ({impact} Impact)",
                    "url": "https://www.forexfactory.com/calendar",
                    "source": "ForexFactory Calendar",
                    "forecast": forecast,
                    "previous": previous
                })
        await set_cached_data("forexfactory", news_items)
    except Exception as e:
        print(f"[Scraper] Failed to fetch ForexFactory calendar: {e}")
    return news_items

async def fetch_crypto_panic_news() -> List[Dict[str, Any]]:
    """
    Fetches latest crypto news from CryptoPanic's public RSS feed.
    Highly accurate, real-time, and free.
    Uses BeautifulSoup to parse HTML/XML safely.
    """
    cached = await get_cached_data("cryptopanic")
    if cached is not None:
        print("[Scraper Cache] Returning cached CryptoPanic news")
        return cached

    url = "https://cryptopanic.com/news/rss/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    news_items = []
    try:
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                # Use html.parser to handle malformed RSS tags safely without requiring lxml
                soup = BeautifulSoup(response.content, "html.parser")
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
        await set_cached_data("cryptopanic", news_items)
    except Exception as e:
        print(f"[Scraper] Failed to fetch CryptoPanic news: {e}")
    return news_items

