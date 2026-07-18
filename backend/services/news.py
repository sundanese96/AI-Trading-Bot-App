import re
from typing import List, Dict, Any

# Simple AFINN-based sentiment analyzer matching Node.js sentiment library
AFINN = {
    "attack": -2, "strike": -2, "war": -2, "escalation": -2, "sanction": -2,
    "funeral": -2, "nuclear": -2, "crisis": -3, "crash": -2, "drop": -1,
    "plunge": -3, "down": -1, "fall": -1, "negative": -2, "bad": -2,
    "strengthen": 2, "strong": 2, "weak": -2, "weaken": -2, "gain": 2,
    "up": 1, "rise": 1, "surge": 2, "growth": 2, "positive": 2, "good": 2,
    "win": 4, "victory": 4, "defeat": -2, "loss": -3, "lost": -2,
    "serangan": -2, "perang": -2, "rudal": -2, "militer": -2, "bom": -2,
    "sanksi": -2, "konflik": -2, "krisis": -3, "jatuh": -2, "turun": -1,
    "longsor": -3, "buruk": -2, "menguat": 2, "kuat": 2, "lemah": -2,
    "melemah": -2, "naik": 1, "tumbuh": 2, "positif": 2, "baik": 2,
    "menang": 4, "kemenangan": 4, "kalah": -2, "rugi": -3
}

def analyze_sentiment(text: str) -> Dict[str, Any]:
    # Tokenize and clean words
    words = text.lower().split()
    score = 0
    positive = []
    negative = []
    tokens = []
    
    for w in words:
        # clean word punctuation
        w_clean = re.sub(r'[^\w]', '', w)
        if not w_clean:
            continue
        tokens.append(w_clean)
        if w_clean in AFINN:
            val = AFINN[w_clean]
            score += val
            if val > 0:
                positive.append(w_clean)
            else:
                negative.append(w_clean)
                
    return {
        "score": score,
        "comparative": score / max(1, len(tokens)),
        "positive": positive,
        "negative": negative,
        "tokens": tokens
    }

# Initial news feed
news_feed = [
    {
        "id": 'n-1',
        "time": '09:12:00',
        "headline": 'US CPI MoM Dirilis 0.4% vs Perkiraan 0.2% - DXY Menguat Tajam',
        "category": 'MACRO',
        "impact": 'CRITICAL',
        "source": 'ForexFactory (Red Folder)',
        "details": 'Data inflasi AS menunjukkan ketahanan ekonomi yang tinggi, memicu spekulasi bahwa Federal Reserve akan menaikkan suku bunga atau menahannya lebih lama. Dolar AS (DXY) langsung menguat, memberikan tekanan berat pada pasar kripto.',
        "forecast": '0.2%',
        "previous": '0.3%',
        "isTriggeredShort": True,
        "isTriggeredGold": False,
        "summaryId": 'Inflasi AS di atas perkiraan memperkuat DXY. Deviasi: |0.4% - 0.2%| = 0.2% (Signifikan). Sinyal: SHORT ALTCOINS terkonfirmasi karena USD menguat.',
    },
    {
        "id": 'n-1-b',
        "time": '08:50:00',
        "headline": 'US Non-Farm Employment Change (NFP) Dirilis 272K vs Perkiraan 185K',
        "category": 'MACRO',
        "impact": 'HIGH',
        "source": 'ForexFactory (Red Folder)',
        "details": 'Rilis data pekerjaan NFP AS melesat jauh melampaui estimasi konsensus pasar, memperkuat prospek suku bunga tinggi The Fed.',
        "forecast": '185K',
        "previous": '175K',
        "isTriggeredShort": True,
        "isTriggeredGold": False,
        "summaryId": 'Pekerjaan NFP melampaui perkiraan. Suku bunga tinggi dapat dipertahankan. Sinyal: SHORT.',
    },
    {
        "id": 'n-1-c',
        "time": '08:48:00',
        "headline": 'FOMC Interest Rate Decision Dirilis 5.50% vs Perkiraan 5.50%',
        "category": 'MACRO',
        "impact": 'HIGH',
        "source": 'ForexFactory (Red Folder)',
        "details": 'Federal Reserve mengumumkan suku bunga acuan tetap di level 5.50%, sesuai ekspektasi pasar namun mempertahankan nada hawkish.',
        "forecast": '5.50%',
        "previous": '5.50%',
        "isTriggeredShort": False,
        "isTriggeredGold": False,
        "summaryId": 'Suku bunga tetap sesuai perkiraan. Nada hawkish dipertahankan. Sinyal: NEUTRAL.',
    },
    {
        "id": 'n-2',
        "time": '08:45:00',
        "headline": 'BREAKING: Rudal Tak Dikenal Hantam Wilayah Perbatasan Timur Tengah',
        "category": 'GEOPOLITICS',
        "impact": 'CRITICAL',
        "source": 'Reuters Scraper',
        "details": 'Serangan udara dilaporkan memicu kepanikan massal di wilayah penghasil minyak utama. Sentimen safe-haven langsung aktif, menyebabkan harga Emas (XAU) melonjak, sementara Bitcoin mengalami aksi jual cepat akibat penarikan risiko modal global.',
        "isTriggeredShort": True,
        "isTriggeredGold": True,
        "summaryId": 'Ketegangan geopolitik meningkat ekstrem. Emas naik drastis (safe-haven), Bitcoin jatuh. Sinyal: SHORT ALTCOINS dan LONG GOLD terkonfirmasi secara bersamaan.',
    },
    {
        "id": 'n-3',
        "time": '07:30:00',
        "headline": 'Aktivitas Dompet Paus Bitcoin Terlihat Mengakumulasi di Kisaran $62k',
        "category": 'GENERAL',
        "impact": 'NEUTRAL',
        "source": 'Binance API Monitor',
        "details": 'Data on-chain menunjukkan beberapa whale besar mulai menyerap pasokan Bitcoin di area support psikologis. Volatilitas masih tergolong normal.',
        "isTriggeredShort": False,
        "isTriggeredGold": False,
        "summaryId": 'Konsolidasi pasar normal tanpa deviasi geopolitik atau makroekonomi yang mendesak.',
    },
]
