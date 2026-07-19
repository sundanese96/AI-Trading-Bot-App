"""News and crisis trigger endpoints extracted from main.py."""
import time
from fastapi import APIRouter

from backend.services.news import news_feed, news_feed_lock
from backend.services.market import current_panic
from backend.models.schemas import TriggerCrisisRequest

router = APIRouter()


@router.get("/api/news")
async def get_news():
    return news_feed


@router.post("/api/trigger-crisis")
async def trigger_crisis(req: TriggerCrisisRequest):
    global current_panic
    
    if req.type == "GEOPOLITICS":
        current_panic.update({
            "active": True,
            "type": "GEOPOLITICS",
            "title": req.headline or "Darurat Geopolitik Terdeteksi!",
            "timeLeft": 20
        })
        async with news_feed_lock:
            news_feed.insert(0, {
                "id": f"crisis-{int(time.time()*1000)}",
                "time": time.strftime("%H:%M:%S"),
                "headline": req.headline or "DARURAT: Eskalasi Militer Dilaporkan",
                "category": "GEOPOLITICS",
                "impact": "CRITICAL",
                "source": "Market Panic Event",
                "details": req.details or "Pasar merespons krisis dengan mengalirkan dana ke safe-haven Emas.",
                "isTriggeredShort": True,
                "isTriggeredGold": True,
                "summaryId": "Sistem mendeteksi kata kunci serangan/krisis. Emas Naik + Bitcoin Turun. Sinyal: SHORT ALTCOINS valid."
            })
            if len(news_feed) > 50: news_feed.pop()
        return { "status": "ok" }
        
    elif req.type == "MACRO":
        current_panic.update({
            "active": True,
            "type": "MACRO",
            "title": req.headline or "Kejutan Data Makroekonomi AS!",
            "timeLeft": 20
        })
        new_item = {
            "id": f"news-{int(time.time() * 1000)}",
            "time": time.strftime("%H:%M:%S"),
            "headline": req.headline or "MACRO ALERT: Angka NFP AS Melambung Tinggi dari Konsensus (+310k vs +170k)",
            "category": "MACRO",
            "impact": "CRITICAL",
            "source": "ForexFactory Weekly Poller",
            "details": req.details or "Pertumbuhan lapangan kerja AS yang kuat memicu penguatan Dolar AS (DXY) secara masif. Likuiditas aset berisiko ditarik seketika.",
            "isTriggeredShort": True,
            "isTriggeredGold": False,
            "summaryId": "NFP melesat melampaui forecast. Deviasi positif bagi USD. Sinyal: SHORT ALTCOINS terkonfirmasi."
        }
        async with news_feed_lock:
            news_feed.insert(0, new_item)
        return { "status": "ok", "event": new_item }
        
    else:
        current_panic.update({
            "active": False,
            "type": "NONE",
            "title": "",
            "timeLeft": 0
        })
        return { "status": "ok", "message": "Market stabilized" }
