import httpx
import hashlib
import time
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any

from backend.services import db_manager
from backend.services.news import analyze_sentiment
from backend.config import VERIFY_SSL

# Keyword configuration matching user request
KEYWORDS_MACRO = ['cpi', 'nfp', 'inflation', 'fed', 'fomc', 'interest rate', 'unemployment', 'gdp', 'suku bunga', 'inflasi']
KEYWORDS_GEOPOLITICS = ['geopolitics', 'war', 'strike', 'attack', 'escalation', 'sanction', 'military', 'conflict', 'perang', 'serangan', 'konflik', 'rudal', 'sanksi']
KEYWORDS_CRYPTO = ['crypto', 'cryptocurrency', 'cryptocurrencies', 'bitcoin', 'ethereum', 'solana', 'btc', 'eth', 'sol', 'whale']

ALL_KEYWORDS = KEYWORDS_MACRO + KEYWORDS_GEOPOLITICS + KEYWORDS_CRYPTO

# Global status tracker for background scraping progress
scraping_status = {
    "active": False,
    "progress": "Idle",
    "ingested": 0,
    "current_keyword": ""
}

def determine_category(headline: str) -> str:
    lower = headline.lower()
    if any(kw in lower for kw in KEYWORDS_CRYPTO):
        return "CRYPTO"
    if any(kw in lower for kw in KEYWORDS_GEOPOLITICS):
        return "GEOPOLITICS"
    if any(kw in lower for kw in KEYWORDS_MACRO):
        return "MACRO"
    return "GENERAL"

async def scrape_google_news_historical(start_date: str, end_date: str, custom_keywords: List[str] = None) -> int:
    """
    Scrapes Google News RSS for Reuters articles containing specified keywords.
    Format of dates: YYYY-MM-DD
    """
    global scraping_status
    keywords_to_use = custom_keywords if custom_keywords else ALL_KEYWORDS
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    unique_headlines = set()
    ingested_count = 0
    
    scraping_status.update({
        "active": True,
        "progress": f"Memulai pengerukan dari {start_date} s.d. {end_date}...",
        "ingested": 0,
        "current_keyword": ""
    })
    
    # Calculate query_end_date as end_date + 1 day because Google News "before:" is exclusive
    try:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        query_end_date = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception:
        query_end_date = end_date
    
    try:
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            for kw in keywords_to_use:
                scraping_status.update({
                    "progress": f"Mencari kata kunci: '{kw}'...",
                    "current_keyword": kw,
                    "ingested": ingested_count
                })
                
                # Query format for Google News: site:reuters.com + keyword + timeframe
                query = f"site:reuters.com {kw} after:{start_date} before:{query_end_date}"
                url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
                
                try:
                    response = await client.get(url, headers=headers, timeout=15.0)
                    if response.status_code != 200:
                        print(f"[Scraper] Failed to fetch for keyword '{kw}': Status {response.status_code}")
                        continue
                    
                    soup = BeautifulSoup(response.content, "xml")
                    items = soup.find_all("item")
                    
                    for item in items:
                        title_tag = item.find("title")
                        link_tag = item.find("link")
                        pub_date_tag = item.find("pubDate")
                        
                        title = title_tag.get_text().strip() if title_tag else ""
                        link = link_tag.get_text().strip() if link_tag else ""
                        pub_date_str = pub_date_tag.get_text().strip() if pub_date_tag else ""
                        
                        if not title or title in unique_headlines:
                            continue
                            
                        unique_headlines.add(title)
                        
                        # Parse pubDate to millisecond timestamp
                        try:
                            dt = parsedate_to_datetime(pub_date_str)
                            timestamp = int(dt.timestamp() * 1000)
                        except Exception:
                            timestamp = int(time.time() * 1000)
                        
                        # Sentiment Analysis
                        sentiment_res = analyze_sentiment(title)
                        score = sentiment_res["score"]
                        
                        # Categorize news
                        category = determine_category(title)
                        
                        # Create clean headline details
                        news_item = {
                            "id": f"news-{hashlib.md5(title.encode('utf-8')).hexdigest()[:16]}",
                            "title": title,
                            "url": link,
                            "source": "Reuters (via Google News)",
                            "timestamp": timestamp,
                            "category": category,
                            "sentiment_score": score
                        }
                        
                        await db_manager.insert_news_headline(news_item)
                        ingested_count += 1
                        
                except Exception as e:
                    print(f"[Scraper] Error scraping keyword '{kw}': {e}")
                    
                # Rate limit friendly sleep
                await asyncio.sleep(0.5)
                
        scraping_status.update({
            "progress": f"Pengerukan selesai! Berhasil menyimpan {ingested_count} berita.",
            "ingested": ingested_count,
            "current_keyword": ""
        })
    except Exception as general_err:
        scraping_status.update({
            "progress": f"Error saat pengerukan: {str(general_err)}",
        })
    finally:
        scraping_status["active"] = False
        
    print(f"[Scraper] Ingested {ingested_count} historical news articles between {start_date} and {end_date}.")
    return ingested_count
