import asyncio
import httpx
import json

async def main():
    url = "http://localhost:8080/v1/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Test our optimized condensed system instruction and prompt
    system_instruction = """Anda adalah analis kuantitatif senior dan AI Trading Bot. Klasifikasikan arah harga Crypto, XAU, dan USD Index dalam 15 menit berikutnya berdasarkan berita baru.

[CONCISE THINKING RULE]
Batasi proses berpikir (thinking/reasoning) Anda hingga maksimal 150 kata! Berpikirlah secara sangat singkat dan padat, lalu segera keluarkan output JSON.

Patuhi aturan:
1. Jika berita netral atau tidak berdampak nyata, berikan keputusan "HOLD".
2. Confidence score untuk LONG atau SHORT maksimal 50%.
3. Berikan rekomendasi leverage (max 5x) dan stop loss (max 2.5%).

Kembalikan respons dalam format JSON dengan struktur persis seperti berikut:
{
  "isGeopolitical": true/false,
  "isMacro": true/false,
  "crisisKeywords": ["kata_kunci"],
  "sentiment": "CRITICAL" atau "NEGATIVE" atau "NEUTRAL" atau "POSITIVE",
  "impactScore": 0-100,
  "macroDetails": {
    "eventName": "N/A",
    "actualValue": "N/A",
    "forecastValue": "N/A",
    "deviation": 0.0,
    "usdStrengthened": false
  },
  "assetsImpact": [
    {"symbol": "BTC", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0},
    {"symbol": "SOL", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0},
    {"symbol": "XAU", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0},
    {"symbol": "DXY", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0}
  ],
  "analysisSummary": "Analisis singkat.",
  "tradeDecision": {
    "decision": "SHORT" atau "LONG" atau "HOLD",
    "targetAsset": "SOL" atau "BTC" atau "ETH",
    "confidence": 0-50,
    "recommendedLeverage": "5x",
    "recommendedStopLoss": "2.5%",
    "strategyReasoning": "Alasan singkat."
  }
}"""
    
    prompt = """
=== LIVE REAL-TIME MARKET PRICES ===
Bitcoin (BTC): $65000.0 (+1.2% 24h)
Solana (SOL): $140.0 (-2.5% 24h)

=== CALCULATED MARKET VOLATILITY DATA ===
BTC 120-tick volatility: 0.15%

=== CRYPTO FEAR & GREED SENTIMENT ===
Fear & Greed Index: 25 (Extreme Fear)

=== GLOBAL NEWS SENTIMENT CORRELATION ===
Current News Sentiment Score: -45
News Sentiment Classification: NEGATIVE

=== RECENT GLOBAL MARKET NEWS HISTORY ===
[14:00 - GENERAL] Fed Chairman signals potential rate hikes.

=== REFERENSI ANALOGI KEJADIAN MASA LALU (RAG) ===
Tidak ditemukan kejadian serupa.

=== NEW INCOMING HEADLINE TO ANALYZE ===
"War erupts in Middle East, triggering global panic"

Gunakan data real-time, volatilitas pasar, sentimen berita, indeks Fear & Greed, dan RAG di atas untuk menganalisis headline baru. Klasifikasikan arah, dampak, dan keputusan trading otomatis dalam format JSON persis sesuai instruksi sistem."""

    payload = {
        "model": "/media/sun/DATA/AI_Model_Local/Ornith-1.0-35B-A3B-MXFP4_MOE_Q8_0_F16-Imatrix.gguf",
        "temperature": 0.6,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "max_tokens": 2048
    }

    print("Sending request to local LLM server...")
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, headers=headers, json=payload, timeout=300.0)
            print(f"Status Code: {response.status_code}")
            print("Response Body:")
            print(response.text)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
