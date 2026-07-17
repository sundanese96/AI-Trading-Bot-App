import aiosqlite
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_FILE = Path(__file__).resolve().parent.parent / "database.db"

async def init_db():
    """Initializes the database, creates tables, and seeds initial historical events if empty."""
    async with aiosqlite.connect(DB_FILE) as db:
        # Create economic_events table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS economic_events (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                datetime TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                actual TEXT,
                forecast TEXT,
                impact TEXT,
                symbol TEXT NOT NULL
            )
        """)
        
        # Create news_headlines table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news_headlines (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT,
                source TEXT,
                timestamp INTEGER NOT NULL,
                category TEXT,
                sentiment_score REAL
            )
        """)
        await db.commit()

        # Evolve schema: Add return/response columns if not present
        for table in ["economic_events", "news_headlines"]:
            for col in ["return_15m REAL", "return_1h REAL", "return_4h REAL", "market_response_populated INTEGER DEFAULT 0"]:
                try:
                    await db.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
                except aiosqlite.OperationalError:
                    # Column already exists
                    pass
        await db.commit()

        # Seed initial 17 core events if economic_events is empty
        async with db.execute("SELECT COUNT(*) FROM economic_events") as cursor:
            count_row = await cursor.fetchone()
            if count_row and count_row[0] == 0:
                print("[DB] Seeding 17 initial historical events...")
                from datetime import datetime, timezone
                
                seed_events = [
                    ('event-1', 'Rilis Data CPI MoM (U.S. Inflation)', '2026-03-12 19:30:00', '0.4%', '0.3%', 'USD Stronger', 'BTCUSDT'),
                    ('event-2', 'Non-Farm Employment Change (NFP)', '2026-04-03 19:30:00', '272K', '185K', 'USD Stronger', 'BTCUSDT'),
                    ('event-3', 'Keputusan Suku Bunga FOMC', '2026-05-01 01:00:00', '4.75%', '5.00%', 'USD Weaker', 'BTCUSDT'),
                    ('event-4', 'Eskalasi Geopolitik Timur Tengah', '2026-05-18 14:15:00', 'Krisis Selat', 'Tensi Naik', 'Geopolitical Crisis', 'BTCUSDT'),
                    ('event-5', 'Rilis Data PCE Core Inflation', '2026-06-11 19:30:00', '0.1%', '0.2%', 'USD Weaker', 'BTCUSDT'),
                    ('event-6', 'Serangan Siber Skala Global di Pelabuhan Barat', '2026-06-25 08:45:00', 'Krisis Logistik', 'Normal', 'Geopolitical Crisis', 'BTCUSDT'),
                    ('event-7', 'U.S. Presidential Election (Donald Trump Victory)', '2024-11-06 08:00:00', 'Trump Win', 'Tight Race', 'USD Weaker', 'BTCUSDT'),
                    ('event-8', 'Pemangkasan Suku Bunga Fed 50 bps', '2024-09-18 18:00:00', '4.75%', '5.00%', 'USD Weaker', 'BTCUSDT'),
                    ('event-9', 'Eskalasi Geopolitik Konflik Laut Merah', '2024-01-12 14:00:00', 'Serangan Udara', 'Tensi Tinggi', 'Geopolitical Crisis', 'BTCUSDT'),
                    ('event-10', 'Rilis Data NFP AS Mengejutkan Negatif', '2024-08-02 12:30:00', '114K', '176K', 'USD Weaker', 'BTCUSDT'),
                    ('event-11', 'Rilis Data CPI AS Panas (Inflasi Tinggi)', '2024-04-10 12:30:00', '3.5%', '3.4%', 'USD Stronger', 'BTCUSDT'),
                    ('event-12', 'Krisis Likuiditas Perbankan Regional AS', '2025-03-15 10:00:00', 'Bank Bailout', 'Stabil', 'Geopolitical Crisis', 'BTCUSDT'),
                    ('event-13', 'Krisis Silicon Valley Bank (SVB Bailout)', '2023-03-10 14:00:00', 'USD 200B Collapse', 'Stabil', 'Geopolitical Crisis', 'BTCUSDT'),
                    ('event-14', 'Rilis CPI AS Terpanas 2023 (Suku Bunga Tinggi)', '2023-06-13 12:30:00', '4.0%', '4.1%', 'USD Stronger', 'BTCUSDT'),
                    ('event-15', 'Pemberontakan Geopolitik Wagner Group Rusia', '2023-06-24 07:00:00', 'Krisis Militer', 'Normal', 'Geopolitical Crisis', 'BTCUSDT'),
                    ('event-16', 'Ketegangan Timur Tengah Konflik Gaza Outbreak', '2023-10-07 05:00:00', 'Conflict Outbreak', 'Stabil', 'Geopolitical Crisis', 'BTCUSDT'),
                    ('event-17', 'Rilis NFP AS Positif Ekstrim Suku Bunga Naik', '2023-02-03 13:30:00', '517K', '185K', 'USD Stronger', 'BTCUSDT')
                ]
                
                for ev in seed_events:
                    # Convert date to millisecond timestamp in UTC timezone
                    dt = datetime.strptime(ev[2], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    ts = int(dt.timestamp() * 1000)
                    
                    await insert_economic_event({
                        "id": ev[0],
                        "name": ev[1],
                        "datetime": ev[2],
                        "timestamp": ts,
                        "actual": ev[3],
                        "forecast": ev[4],
                        "impact": ev[5],
                        "symbol": ev[6]
                    })
    print(f"[DB] SQLite database initialized at {DB_FILE}")

async def insert_economic_event(event: Dict[str, Any]):
    """Inserts or replaces an economic event in the database."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            INSERT OR REPLACE INTO economic_events (id, name, datetime, timestamp, actual, forecast, impact, symbol)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event["id"],
            event["name"],
            event["datetime"],
            event["timestamp"],
            str(event.get("actual", "N/A")),
            str(event.get("forecast", "N/A")),
            event["impact"],
            event.get("symbol", "BTCUSDT")
        ))
        await db.commit()

async def insert_news_headline(news: Dict[str, Any]):
    """Inserts or replaces a news headline in the database."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            INSERT OR REPLACE INTO news_headlines (id, title, url, source, timestamp, category, sentiment_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            news["id"],
            news["title"],
            news.get("url", ""),
            news.get("source", "Unknown"),
            news["timestamp"],
            news.get("category", "GENERAL"),
            news.get("sentiment_score", 0.0)
        ))
        await db.commit()

async def get_all_economic_events() -> List[Dict[str, Any]]:
    """Retrieves all economic events sorted by timestamp."""
    events = []
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM economic_events ORDER BY timestamp DESC") as cursor:
            async for row in cursor:
                events.append({
                    "id": row["id"],
                    "name": row["name"],
                    "datetime": row["datetime"],
                    "timestamp": row["timestamp"],
                    "actual": row["actual"],
                    "forecast": row["forecast"],
                    "impact": row["impact"],
                    "symbol": row["symbol"]
                })
    return events

async def get_economic_events_by_range(start_time: int, end_time: int) -> List[Dict[str, Any]]:
    """Retrieves economic events within a specific timestamp range (in ms)."""
    events = []
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM economic_events WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp DESC",
            (start_time, end_time)
        ) as cursor:
            async for row in cursor:
                events.append({
                    "id": row["id"],
                    "name": row["name"],
                    "datetime": row["datetime"],
                    "timestamp": row["timestamp"],
                    "actual": row["actual"],
                    "forecast": row["forecast"],
                    "impact": row["impact"],
                    "symbol": row["symbol"]
                })
    return events

async def get_news_by_range(start_time: int, end_time: int, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves news headlines within a timestamp range, optionally filtering by keyword."""
    news = []
    query = "SELECT * FROM news_headlines WHERE timestamp >= ? AND timestamp <= ?"
    params = [start_time, end_time]
    
    if keyword:
        query += " AND (title LIKE ? OR category LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
        
    query += " ORDER BY timestamp DESC"
    
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, tuple(params)) as cursor:
            async for row in cursor:
                news.append({
                    "id": row["id"],
                    "title": row["title"],
                    "url": row["url"],
                    "source": row["source"],
                    "timestamp": row["timestamp"],
                    "category": row["category"],
                    "sentiment_score": row["sentiment_score"]
                })
    return news

async def get_news_by_headline(title: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single news headline by its exact title."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM news_headlines WHERE title = ? LIMIT 1", (title,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "title": row["title"],
                    "url": row["url"],
                    "source": row["source"],
                    "timestamp": row["timestamp"],
                    "category": row["category"],
                    "sentiment_score": row["sentiment_score"]
                }
    return None

async def update_economic_event_returns(event_id: str, r15m: float, r1h: float, r4h: float):
    """Updates price returns for a specific economic event and marks it populated."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            UPDATE economic_events 
            SET return_15m = ?, return_1h = ?, return_4h = ?, market_response_populated = 1
            WHERE id = ?
        """, (r15m, r1h, r4h, event_id))
        await db.commit()

async def update_news_headline_returns(news_id: str, r15m: float, r1h: float, r4h: float):
    """Updates price returns for a specific news headline and marks it populated."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            UPDATE news_headlines 
            SET return_15m = ?, return_1h = ?, return_4h = ?, market_response_populated = 1
            WHERE id = ?
        """, (r15m, r1h, r4h, news_id))
        await db.commit()

async def find_similar_past_events(query_title: str, current_timestamp: int, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Finds top N similar past news/economic events with populated market responses.
    Filters by keywords first for speed, then ranks using Jaccard similarity in Python.
    """
    from datetime import datetime, timezone
    
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "is", "are", "was", "were", "of", "about", "vs", "to"}
    words = [w.strip(".,!?\"()").lower() for w in query_title.split()]
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    
    candidates = []
    
    def get_jaccard(txt1: str, txt2: str) -> float:
        t1 = {w.strip(".,!?\"()").lower() for w in txt1.split()}
        t2 = {w.strip(".,!?\"()").lower() for w in txt2.split()}
        t1 = {w for w in t1 if w not in stop_words and len(w) > 2}
        t2 = {w for w in t2 if w not in stop_words and len(w) > 2}
        if not t1 or not t2:
            return 0.0
        return len(t1.intersection(t2)) / len(t1.union(t2))
    
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Search economic_events
        async with db.execute(
            "SELECT * FROM economic_events WHERE market_response_populated = 1 AND timestamp < ? ORDER BY timestamp DESC",
            (current_timestamp,)
        ) as cursor:
            async for row in cursor:
                sim = get_jaccard(query_title, row["name"])
                if sim > 0:
                    candidates.append({
                        "type": "economic_event",
                        "title": row["name"],
                        "timestamp": row["timestamp"],
                        "datetime": row["datetime"],
                        "similarity": sim,
                        "return_15m": row["return_15m"],
                        "return_1h": row["return_1h"],
                        "return_4h": row["return_4h"]
                    })
                    
        # 2. Search news_headlines
        if keywords:
            sql_clauses = []
            params = []
            for kw in keywords[:5]:
                sql_clauses.append("title LIKE ?")
                params.append(f"%{kw}%")
            
            if sql_clauses:
                query = f"""
                    SELECT * FROM news_headlines 
                    WHERE market_response_populated = 1 
                      AND timestamp < ? 
                      AND ({' OR '.join(sql_clauses)})
                    ORDER BY timestamp DESC LIMIT 200
                """
                query_params = [current_timestamp] + params
                async with db.execute(query, tuple(query_params)) as cursor:
                    async for row in cursor:
                        sim = get_jaccard(query_title, row["title"])
                        # Only include if similarity > 0
                        if sim > 0:
                            candidates.append({
                                "type": "news_headline",
                                "title": row["title"],
                                "timestamp": row["timestamp"],
                                "datetime": datetime.fromtimestamp(row["timestamp"]/1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                                "similarity": sim,
                                "return_15m": row["return_15m"],
                                "return_1h": row["return_1h"],
                                "return_4h": row["return_4h"]
                            })
                            
    # Sort: similarity descending, then timestamp descending
    candidates.sort(key=lambda x: (-x["similarity"], -x["timestamp"]))
    
    # Deduplicate titles
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c["title"] not in seen:
            seen.add(c["title"])
            unique_candidates.append(c)
            if len(unique_candidates) >= limit:
                break
                
    return unique_candidates

