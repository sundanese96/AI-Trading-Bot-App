import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio
from backend.services import db_manager
from datetime import datetime

async def test():
    events = await db_manager.get_all_economic_events()
    print("=== EVENTS IN DATABASE ===")
    for e in events[:5]:
        print(f"- [{e['id']}] {e['name']} | Time: {e['datetime']} (TS: {e['timestamp']})")
        
    print("\n=== NEWS HEADLINES IN DATABASE ===")
    async with db_manager.aiosqlite.connect(db_manager.DB_FILE) as db:
        db.row_factory = db_manager.aiosqlite.Row
        async with db.execute("SELECT * FROM news_headlines ORDER BY timestamp DESC LIMIT 20") as cursor:
            async for row in cursor:
                dt = datetime.fromtimestamp(row["timestamp"] / 1000)
                print(f"- [{row['category']}] {row['title']} | Date: {dt} (TS: {row['timestamp']})")

if __name__ == "__main__":
    asyncio.run(test())
