"""Background news scraper loop extracted from main.py."""
import time
import asyncio
from backend.core.logger import logger
from backend.services.news import news_feed, news_feed_lock, analyze_sentiment
from backend.services.scraper import scrape_reuters_news, scrape_bbc_news, fetch_forexfactory_calendar, fetch_crypto_panic_news
from backend.helpers.utils import is_headline_duplicate


async def news_scraper_loop():
    """Background task to periodically scrape news from multiple sources."""
    while True:
        try:
            logger.info("[Scraper] Running periodic news scraper...")
            results = await asyncio.gather(
                scrape_reuters_news(),
                scrape_bbc_news(),
                fetch_forexfactory_calendar(),
                fetch_crypto_panic_news(),
                return_exceptions=True
            )
            
            reuters_news = results[0] if not isinstance(results[0], Exception) else []
            bbc_news = results[1] if not isinstance(results[1], Exception) else []
            ff_news = results[2] if not isinstance(results[2], Exception) else []
            panic_news = results[3] if not isinstance(results[3], Exception) else []
            
            all_scraped = reuters_news + bbc_news + ff_news + panic_news
            
            from backend.database import load_ai_config
            from backend.sentix_adapter import sentix_state
            config = await load_ai_config() or {}
            is_dry_run = config.get("dryRun", True)
            is_locked = config.get("isLocked", False)
            
            bot_settings = sentix_state.get("aiBotSettings", {})
            enabled = bot_settings.get("enabled", False)
            
            for item in all_scraped:
                headline = item["title"]
                if is_headline_duplicate(headline, news_feed):
                    continue
                
                # Check and run live simulation manager if active
                from backend.services.live_sim_manager import live_sim_manager
                if live_sim_manager.active:
                    await live_sim_manager.handle_new_news(item)
                
                if is_dry_run and not is_locked and enabled:
                    from backend.trading.simulator import trigger_automated_trade_sim
                    await trigger_automated_trade_sim(item, config)
                else:
                    sentiment_res = analyze_sentiment(headline)
                    score = sentiment_res["score"]
                    lower = headline.lower()
                    geo_keywords = ['attack', 'strike', 'war', 'escalation', 'sanction', 'funeral', 'nuclear', 'serangan', 'perang', 'rudal', 'militer', 'bom', 'sanksi', 'konflik']
                    is_geo = any(k in lower for k in geo_keywords)
                    macro_keywords = ['nfp', 'cpi', 'fomc', 'gdp', 'inflation', 'fed', 'interest', 'suku bunga', 'pengangguran', 'inflasi', 'gaji', 'pekerjaan']
                    is_macro = any(k in lower for k in macro_keywords)
                    category = "GEOPOLITICS" if is_geo else ("MACRO" if is_macro else "GENERAL")
                    impact = "CRITICAL" if (is_geo or is_macro) else "NEUTRAL"
                    new_item = {
                        "id": f"news-{int(time.time() * 1000)}",
                        "time": time.strftime("%H:%M:%S"),
                        "headline": headline,
                        "category": category,
                        "impact": impact,
                        "source": item["source"],
                        "details": f"Scraped from {item['source']}. Sentiment score: {score}.",
                        "forecast": item.get("forecast", ""),
                        "previous": item.get("previous", ""),
                        "isTriggeredShort": is_geo or is_macro,
                        "isTriggeredGold": is_geo,
                        "summaryId": f"Scraped news. Category: {category}. Short signal: {'ACTIVE' if (is_geo or is_macro) else 'INACTIVE'}."
                    }
                    async with news_feed_lock:
                        news_feed.insert(0, new_item)
                        if len(news_feed) > 50:
                            news_feed.pop()
        except Exception as e:
            logger.error(f"[Scraper] Error in news scraper loop: {e}")
        await asyncio.sleep(180)
