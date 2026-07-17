import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.services import db_manager

async def test():
    # March 12, 2026 event-1 range
    start = 1773318600000 - 12 * 60 * 60 * 1000
    end = 1773318600000 + 12 * 60 * 60 * 1000
    
    print(f"Query range: {start} to {end}")
    
    news = await db_manager.get_news_by_range(start, end)
    print(f"Results count: {len(news)}")
    for n in news:
        print(f"- {n['title']} | TS: {n['timestamp']}")

if __name__ == "__main__":
    asyncio.run(test())
