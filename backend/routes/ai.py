"""AI Analysis and config endpoints extracted from main.py."""
import time
import json
import re
from fastapi import APIRouter, HTTPException

from backend.core.logger import logger
from backend.services.market import assets, current_panic, calculate_asset_volatility, fng_cache, calculate_news_sentiment_index
from backend.services.news import news_feed, news_feed_lock, analyze_sentiment
from backend.services.ai import call_gemini, call_openai, call_anthropic, call_custom, call_semburat_gateway, clean_and_parse_json
from backend.helpers.utils import get_llm_lock, llm_response_cache
from backend.models.schemas import AIAnalyzeRequest, SaveAIConfigRequest, EvaluateRequest
from backend.config import GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, CUSTOM_AI_KEY

router = APIRouter()


@router.get("/api/ai/config")
async def get_ai_config():
    from backend.database import load_ai_config
    return await load_ai_config()


@router.post("/api/ai/config")
async def save_ai_config_endpoint(req: SaveAIConfigRequest):
    from backend.database import save_ai_config
    config_data = {
        "provider": req.provider,
        "customUrl": req.customUrl,
        "customKey": req.customKey,
        "customModel": req.customModel,
        "binanceApiKey": req.binanceApiKey,
        "binanceApiSecret": req.binanceApiSecret,
        "dryRun": req.dryRun,
        "maxDailyLoss": req.maxDailyLoss,
        "maxTradesPerDay": req.maxTradesPerDay,
        "confidenceThreshold": req.confidenceThreshold,
        "telegramBotToken": getattr(req, "telegramBotToken", ""),
        "telegramChatId": getattr(req, "telegramChatId", ""),
        "mlTargetWindow": getattr(req, "mlTargetWindow", 15),
        "mlThresholdPct": getattr(req, "mlThresholdPct", 0.15),
        "mlModelType": getattr(req, "mlModelType", "xgboost"),
        "isLocked": False
    }
    await save_ai_config(config_data)
    return { "status": "ok", "message": "AI and Binance configuration saved and encrypted successfully." }


@router.post("/api/bot/unlock")
async def unlock_bot_endpoint():
    from backend.database import unlock_bot
    await unlock_bot()
    return { "status": "ok", "message": "Bot unlocked successfully." }


@router.post("/api/ai/analyze")
async def analyze_ai(req: AIAnalyzeRequest):
    global current_panic
    
    target_asset = req.targetAsset or "BTC"
    
    from backend.database import load_ai_config, read_database_async, write_database_async, db_lock
    from backend.sentix_adapter import sentix_state
    config = await load_ai_config() or {}
    bot_settings = sentix_state.get("aiBotSettings", {})
    confidence_threshold = bot_settings.get("minConfidence", config.get("confidenceThreshold", 75))
    
    api_key = ""
    if req.provider == "gemini":
        api_key = req.customKey or GEMINI_API_KEY
    elif req.provider == "openai":
        api_key = req.customKey or OPENAI_API_KEY
    elif req.provider == "anthropic":
        api_key = req.customKey or ANTHROPIC_API_KEY
    elif req.provider == "custom":
        api_key = req.customKey or CUSTOM_AI_KEY
    elif req.provider == "semburat":
        api_key = req.customKey or CUSTOM_AI_KEY or "semburat"

    vol_list = []
    for a in assets:
        vol = calculate_asset_volatility(a["history"])
        vol_list.append(f"{a['name']} ({a['symbol']}) 20-tick volatility: {vol['pctVolatility']}% (StdDev: {vol['stdDev']})")
    asset_volatilities = "\n".join(vol_list)

    news_sentiment = calculate_news_sentiment_index(news_feed[:5])
    fear_and_greed_context = f"Current FNG Value: {fng_cache['value']} ({fng_cache['value_classification']})" if fng_cache else "Current FNG Value: 50 (Neutral)"

    has_no_key = not api_key or api_key in ["MY_GEMINI_API_KEY", "MY_OPENAI_API_KEY", "MY_ANTHROPIC_API_KEY"]
    use_fallback = has_no_key and (req.provider not in ["custom", "semburat"] or not req.customUrl)

    if use_fallback:
        logger.info(f"No API key provided for {req.provider}. Using high-fidelity local fallback classifier.")
        lower = req.headline.lower()
        
        geo_keywords = ['attack', 'strike', 'war', 'escalation', 'sanction', 'funeral', 'nuclear', 'serangan', 'perang', 'rudal', 'militer', 'bom', 'sanksi', 'konflik']
        matched_geo = [k for k in geo_keywords if k in lower]
        is_geopolitical = len(matched_geo) > 0

        macro_keywords = ['nfp', 'cpi', 'fomc', 'gdp', 'inflation', 'fed', 'interest', 'suku bunga', 'pengangguran', 'inflasi', 'gaji', 'pekerjaan']
        matched_macro = [k for k in macro_keywords if k in lower]
        is_macro = len(matched_macro) > 0

        sentiment = "NEGATIVE" if (is_geopolitical or is_macro) else "NEUTRAL"
        impact_score = 85 if is_geopolitical else (75 if is_macro else 15)

        assets_impact = [
            { "symbol": 'BTC', "direction": 'DOWN' if (is_geopolitical or is_macro) else 'NEUTRAL', "percentage": -5.5 if is_geopolitical else (-4.2 if is_macro else 0.1) },
            { "symbol": 'SOL', "direction": 'DOWN' if (is_geopolitical or is_macro) else 'NEUTRAL', "percentage": -8.2 if is_geopolitical else (-6.8 if is_macro else 0.2) },
            { "symbol": 'XAU', "direction": 'UP' if is_geopolitical else ('DOWN' if is_macro else 'NEUTRAL'), "percentage": 3.4 if is_geopolitical else (-1.2 if is_macro else -0.1) },
            { "symbol": 'DXY', "direction": 'UP' if (is_geopolitical or is_macro) else 'NEUTRAL', "percentage": 0.5 if is_geopolitical else (1.8 if is_macro else 0.05) }
        ]

        analysis_summary = (
            f"[Sistem Fallback Analitis] Hasil analisis mendeteksi ancaman geopolitik serius berdasarkan kata kunci: \"{', '.join(matched_geo)}\". Emas diprediksi menguat sebagai safe haven (+3.4%), sementara Bitcoin dan Altcoins bersiap jatuh karena aksi de-risking global. Sinyal SHORT sangat direkomendasikan."
            if is_geopolitical else
            (f"[Sistem Fallback Analitis] Hasil analisis mendeteksi deviasi makroekonomi kritis berdasarkan kata kunci: \"{', '.join(matched_macro)}\". Dolar AS diproyeksikan menguat pesat (+1.8%), menekan likuiditas aset kripto secara luas. Sinyal SHORT Altcoin terkonfirmasi."
             if is_macro else
             "[Sistem Fallback Analitis] Judul berita dinilai netral tanpa memicu indikator krisis geopolitik maupun deviasi makroekonomi yang substansial. Sinyal trading tetap tidak aktif.")
        )

        generated_event = {
            "id": f"news-{int(time.time() * 1000)}",
            "time": time.strftime("%H:%M:%S"),
            "headline": req.headline,
            "category": "GEOPOLITICS" if is_geopolitical else ("MACRO" if is_macro else "GENERAL"),
            "impact": "CRITICAL" if (is_geopolitical or is_macro) else "NEUTRAL",
            "source": req.source or "User Live Input",
            "details": f"Hasil analisis mendalam: {analysis_summary}",
            "forecast": getattr(req, "forecast", ""),
            "previous": getattr(req, "previous", ""),
            "isTriggeredShort": is_geopolitical or is_macro,
            "isTriggeredGold": is_geopolitical,
            "summaryId": f"Deviasi Terdeteksi! Kategori: {'Geopolitik' if is_geopolitical else 'Makro' if is_macro else 'Umum'}. Sinyal short kripto: {'AKTIF' if (is_geopolitical or is_macro) else 'NON-AKTIF'}."
        }

        async with news_feed_lock:
            news_feed.insert(0, generated_event)

        if is_geopolitical:
            current_panic.update({ "active": True, "type": "GEOPOLITICS", "title": req.headline, "timeLeft": 15 })
        elif is_macro:
            current_panic.update({ "active": True, "type": "MACRO", "title": req.headline, "timeLeft": 15 })

        trade_decision_fallback = {
            "decision": "SHORT" if (is_geopolitical or is_macro) else "HOLD",
            "targetAsset": target_asset,
            "confidence": 35 if is_geopolitical else (30 if is_macro else 10),
            "recommendedLeverage": "5x" if (is_geopolitical or is_macro) else "N/A",
            "recommendedStopLoss": "2.5%" if (is_geopolitical or is_macro) else "N/A",
            "strategyReasoning": (
                f"Dampak eskalasi geopolitik memicu aliran likuiditas keluar dari koin-koin beta tinggi menuju Emas. Eksekusi SHORT {target_asset} terkonfirmasi. Confidence terbatas (<35%) karena data historis menunjukkan win rate rendah pada timeframe 15 menit."
                if is_geopolitical else
                (f"Data makroekonomi positif untuk Dolar AS memicu lonjakan DXY, yang menekan likuiditas aset kripto secara luas. Rekomendasi SHORT {target_asset}. Confidence terbatas (<30%) karena deviasi historis kecil pada window 15 menit."
                 if is_macro else
                 "Pasar stabil tanpa deviasi ekstrem yang terdeteksi. Disarankan HOLD dan menunggu krisis terkonfirmasi.")
            )
        }

        final_analysis = {
            "isGeopolitical": is_geopolitical,
            "isMacro": is_macro,
            "crisisKeywords": matched_geo,
            "sentiment": sentiment,
            "impactScore": impact_score,
            "macroDetails": {
                "eventName": "Data Makro Input" if is_macro else "N/A",
                "actualValue": "N/A",
                "forecastValue": "N/A",
                "deviation": 0.35 if is_macro else 0.0,
                "usdStrengthened": is_macro
            },
            "assetsImpact": assets_impact,
            "analysisSummary": analysis_summary,
            "tradeDecision": trade_decision_fallback
        }

        try:
            async with db_lock:
                db = await read_database_async()
                if "savedAnalyses" not in db:
                    db["savedAnalyses"] = []
                db["savedAnalyses"].insert(0, {
                    "id": generated_event["id"],
                    "timestamp": int(time.time() * 1000),
                    "headline": req.headline,
                    "source": generated_event["source"],
                    "analysis": final_analysis,
                    "event": generated_event,
                    "marketMetrics": {
                        "volatilities": [{ "symbol": a["symbol"], "pctVol": calculate_asset_volatility(a["history"])["pctVolatility"] } for a in assets],
                        "fng": int(fng_cache["value"]),
                        "newsSentimentScore": news_sentiment["score"]
                    }
                })
                db["savedAnalyses"] = db["savedAnalyses"][:50]
                await write_database_async(db)
        except Exception as db_err:
            logger.error(f"[DATABASE] Failed to save fallback analysis: {db_err}")

        return {
            "fallback": True,
            "provider": "fallback",
            "analysis": final_analysis,
            "event": generated_event
        }

    system_instruction = """Anda adalah analis kuantitatif senior dan AI Trading Bot di Bloomberg Terminal yang bertugas memindai berita krisis global ekstrem dan mengklasifikasikan arah harga Crypto, Emas (XAU), dan DXY (USD Index) dalam 15 menit berikutnya.
Anda HARUS membaca data harga pasar real-time, tingkat volatilitas terukur (volatility), sentimen berita kumulatif (news sentiment score), dan ketakutan pasar (Fear & Greed Index) yang disediakan untuk merumuskan tradeDecision dan confidence score yang sangat logis dan konsisten sebagai penunjang keputusan user.

=== REFERENSI ANALOGI KEJADIAN MASA LALU (RAG) ===
Di bagian bawah prompt Anda akan diberikan daftar kejadian sejenis dari database historis berserta performa lilin (candle) harga BTCUSDT setelah rilis tersebut.
Anda HARUS mempertimbangkan data analogi historis ini secara serius untuk meredam kecenderungan over-predict/over-reaction. Gunakan persentase penguatan/pelemahan aslinya sebagai benchmarks/anchor reaksi pasar (dan sebutkan dalam strategyReasoning Anda jika relevan).

=== DATA HISTORIS BACKTEST (KORELARSI BERITA & HARGA) ===
Gunakan data statistik historis riil (2024-2026) berikut sebagai referensi utama untuk menentukan arah dan confidence score:
1. Rilis CPI MoM AS > Forecast (USD Menguat):
   - BTCUSDT: Rata-rata pergerakan harga hanya turun -0.135% (bukan -1.8%) dalam 15 menit pertama.
   - Altcoins (SOL, ETH): Rata-rata pergerakan rata-rata hanya -0.070% dalam 15 menit pertama (bukan -3.5% hingga -4.5%).
   - Win Rate sinyal SHORT BTC & Altcoins: Hanya 20% - 30% (bukan 88%).
   - CATATAN KELAYAKAN: Deviasi CPI panas TIDAK cukup kuat/konsisten untuk dijadikan dasar pengambilan keputusan directional trade (SHORT) dengan keyakinan tinggi.
2. Rilis NFP AS > Forecast (USD Menguat):
   - BTCUSDT: Rata-rata pergerakan harga hanya turun -0.065% (bukan -1.5%) dalam 15 menit pertama.
   - Altcoins (SOL, ETH): Rata-rata pergerakan rata-rata hanya -0.011% dalam 15 menit pertama.
   - Win Rate sinyal SHORT BTC & Altcoins: Hanya 23.5% - 38.2% (bukan 85%).
   - CATATAN KELAYAKAN: Rilis NFP panas tidak memberikan arah pergerakan jangka pendek yang meyakinkan secara statistik.
3. Eskalasi Geopolitik Timur Tengah / Krisis Militer:
   - BTCUSDT: Rata-rata pergerakan harga justru NAIK tipis +0.028% (bukan turun -3.2%) dalam 15 menit pertama.
   - Altcoins (SOL, ETH): Rata-rata pergerakan rata-rata hanya naik/turun +0.027% dalam 15 menit pertama (bukan turun -5.5% hingga -8.2%).
   - Win Rate sinyal SHORT BTC/Altcoins: Hanya 5.13% - 17.95% dari 78 sample event riil.
   - CATATAN UTAMA: Asumsi lama bahwa eskalasi geopolitik secara instan memicu kejatuhan pasar crypto terbukti SALAH secara statistik pada timeframe super pendek 15 menit. Pasar crypto cenderung flat atau berfluktuasi tanpa arah yang jelas.
4. Emas (XAU):
   - Data pergerakan 15-menit historis saat ada eskalasi geopolitik tidak tersedia, jangan buat klaim spesifik tentang pergerakan historis instan untuk XAU/USD hingga data 5m historis XAU berhasil didapatkan.

=== ATURAN PENGAMANAN EXTRA (CRITICAL SAFETY RULES) ===
1. Bot harus bersikap SANGAT KRITIS dan HATI-HATI. Jangan mudah terpicu oleh berita yang bersifat spekulatif atau tidak memiliki dampak nyata.
2. Jika berita dinilai netral, tidak memiliki deviasi angka makro yang signifikan, atau tidak mengandung ancaman geopolitik riil, Anda WAJIB memberikan keputusan "HOLD" dengan confidence score rendah (di bawah 30).
3. Berdasarkan data historis riil, pergerakan harga dalam window 15 menit pasca-event (baik makroekonomi maupun geopolitik) cenderung SANGAT KECIL (berkisar < 0.15% rata-rata) dan TIDAK KONSISTEN ARAHNYA. Anda tidak boleh berasumsi bahwa krisis besar atau berita dramatis pasti memicu pergerakan searah yang dapat diprediksi secara instan. Tetap prioritaskan keputusan konservatif (seperti HOLD).
4. CAP CONFIDENCE SCORE: Mengingat win rate statistik aktual tidak pernah melebihi 48% di kategori mana pun yang divalidasi, Anda dilarang memberikan confidence score untuk directional trade (LONG atau SHORT) yang melebihi 40% - 50%. Tuliskan secara jujur tingkat ketidakpastian tinggi ini pada strategyReasoning (misal, merujuk pada rendahnya keunggulan statistik historis/win rate/mean return yang kecil).
5. Berikan rekomendasi leverage yang rasional (maksimal 5x) dan stop loss yang ketat (maksimal 2.5%) untuk melindungi modal pengguna.

Anda harus mengembalikan response dalam format JSON yang valid dan bersih dengan struktur persis seperti berikut:
{
  "isGeopolitical": true/false,
  "isMacro": true/false,
  "crisisKeywords": ["kata_kunci1", "kata_kunci2"],
  "sentiment": "CRITICAL" atau "NEGATIVE" atau "NEUTRAL" atau "POSITIVE",
  "impactScore": 0-100,
  "macroDetails": {
    "eventName": "Nama rilis makro seperti NFP, CPI jika isMacro true, jika tidak tulis N/A",
    "actualValue": "N/A",
    "forecastValue": "N/A",
    "deviation": 0.0,
    "usdStrengthened": true/false
  },
  "assetsImpact": [
    {"symbol": "BTC", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": -0.135},
    {"symbol": "SOL", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": -0.07},
    {"symbol": "XAU", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0},
    {"symbol": "DXY", "direction": "UP"/"DOWN"/"NEUTRAL", "percentage": 0.0}
  ],
  "analysisSummary": "Analisis kuantitatif mendalam dalam bahasa Indonesia, hubungkan dengan volatilitas pasar saat ini dan skor sentimen berita yang disediakan.",
  "tradeDecision": {
    "decision": "SHORT" atau "LONG" atau "HOLD",
    "targetAsset": "SOL" atau "BTC" atau "ETH" or "XAU" or "XRP",
    "confidence": 0-50,
    "recommendedLeverage": "5x" atau "N/A",
    "recommendedStopLoss": "2.5%" atau "N/A",
    "strategyReasoning": "Uraian kuantitatif mengapa bot merekomendasikan keputusan tersebut dengan confidence score tersebut, merujuk langsung pada volatilitas aset dan data statistik korelasi historis riil."
  }
}"""

    system_instruction = system_instruction.replace(
        "Anda adalah analis kuantitatif senior dan AI Trading Bot di Bloomberg Terminal yang bertugas memindai berita krisis global ekstrem dan mengklasifikasikan arah harga Crypto, Emas (XAU), dan DXY (USD Index) dalam 15 menit berikutnya.",
        "Anda adalah analis kuantitatif senior dan AI Trading Bot di Bloomberg Terminal yang bertugas memindai berita krisis global ekstrem dan mengklasifikasikan arah harga Crypto, Emas (XAU), dan DXY (USD Index) dalam 15 menit berikutnya.\n"
        f"Anda HARUS memfokuskan analisis dan keputusan trading (tradeDecision) secara khusus untuk koin target aktif: {target_asset}. Pilihan asset pada output tradeDecision.targetAsset WAJIB berupa '{target_asset}'."
    )

    system_instruction_to_use = system_instruction
    if req.provider == "custom":
        limit_rag = 1
        system_instruction_to_use = """Anda adalah analis kuantitatif senior dan AI Trading Bot. Klasifikasikan arah harga Crypto, XAU, dan USD Index dalam 15 menit berikutnya berdasarkan berita baru.
""" + f"Anda HARUS memfokuskan analisis dan keputusan trading (tradeDecision) secara khusus untuk koin target aktif: {target_asset}. Pilihan asset pada output tradeDecision.targetAsset WAJIB berupa '{target_asset}'.\n" + """
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

    analogies_context_list = []
    try:
        from backend.services.db_manager import find_similar_past_events
        current_time_ms = int(time.time() * 1000)
        limit_rag = 1 if req.provider == "custom" else 3
        matches = await find_similar_past_events(req.headline, current_time_ms, limit=limit_rag)
        if matches:
            analogies_context_list.append(f"Untuk berita: \"{req.headline}\"")
            for idx, m in enumerate(matches):
                pct_15m = f"{m['return_15m']*100:+.4f}%" if m['return_15m'] is not None else "N/A"
                pct_1h = f"{m['return_1h']*100:+.4f}%" if m['return_1h'] is not None else "N/A"
                pct_4h = f"{m['return_4h']*100:+.4f}%" if m['return_4h'] is not None else "N/A"
                analogies_context_list.append(
                    f"  * Analogi {idx+1}: '{m['title']}' ({m['type']})\n"
                    f"    Tanggal: {m['datetime']} (Jaccard Match: {m['similarity']:.2%})\n"
                    f"    Respon Lilin BTCUSDT: 15m={pct_15m} | 1h={pct_1h} | 4h={pct_4h}"
                )
    except Exception as db_err:
        logger.error(f"[RAG Live] Failed to fetch analogies: {db_err}")

    analogies_context = "\n".join(analogies_context_list) if analogies_context_list else "Tidak ditemukan kejadian serupa ber-analog respon pasar di database historis."

    current_prices_context = "\n".join([f"{a['name']} ({a['symbol']}): ${a['price']} ({'+' if a['change24h'] > 0 else ''}{a['change24h']}% 24h)" for a in assets])
    
    if req.provider == "custom":
        recent_news_context = "\n".join([f"[{n['time']} - {n['category']}] {n['headline']}" for n in news_feed[:2]])
    else:
        recent_news_context = "\n".join([f"[{n['time']} - {n['category']}] {n['headline']}: {n['details']}" for n in news_feed[:4]])

    prompt = f"""
=== LIVE REAL-TIME MARKET PRICES ===
{current_prices_context}

=== CALCULATED MARKET VOLATILITY DATA ===
{asset_volatilities}

=== CRYPTO FEAR & GREED SENTIMENT ===
{fear_and_greed_context}

=== GLOBAL NEWS SENTIMENT CORRELATION ===
Current News Sentiment Score: {news_sentiment['score']} (-100 to +100 scale)
News Sentiment Classification: {news_sentiment['classification']}

=== RECENT GLOBAL MARKET NEWS HISTORY ===
{recent_news_context}

=== REFERENSI ANALOGI KEJADIAN MASA LALU (RAG) ===
{analogies_context}

=== NEW INCOMING HEADLINE TO ANALYZE ===
"{req.headline}"

Gunakan data real-time, volatilitas pasar, sentimen berita, indeks Fear & Greed, dan RAG di atas untuk menganalisis headline baru. Klasifikasikan arah, dampak, dan keputusan trading otomatis dalam format JSON persis sesuai instruksi sistem."""

    try:
        response_text = ""
        used_model = ""

        if req.provider == "gemini":
            used_model = "gemini-2.0-flash"
        elif req.provider == "openai":
            used_model = req.customModel or "gpt-4o-mini"
        elif req.provider == "anthropic":
            used_model = req.customModel or "claude-3-5-sonnet-20241022"
        elif req.provider == "custom":
            used_model = req.customModel or "custom-model"
        elif req.provider == "semburat":
            used_model = req.customModel or "claude-3-5-sonnet-20241022"

        cache_key = (req.provider, used_model, req.headline)
        
        llm_lock_obj = get_llm_lock()
        async with llm_lock_obj:
            if cache_key in llm_response_cache:
                response_text = llm_response_cache[cache_key]
                logger.info(f"[LLM CACHE] Serving cached LLM response for: '{req.headline}'")
            else:
                try:
                    if req.provider == "gemini":
                        response_text = await call_gemini(api_key, used_model, system_instruction_to_use, prompt)
                    elif req.provider == "openai":
                        response_text = await call_openai(api_key, used_model, system_instruction_to_use, prompt)
                    elif req.provider == "anthropic":
                        response_text = await call_anthropic(api_key, used_model, system_instruction_to_use, prompt)
                    elif req.provider == "custom":
                        response_text = await call_custom(api_key, req.customUrl, used_model, system_instruction_to_use, prompt)
                    elif req.provider == "semburat":
                        response_text = await call_semburat_gateway(req.customUrl, used_model, system_instruction_to_use, prompt)
                    else:
                        raise ValueError(f"Unknown provider: {req.provider}")
                except Exception as call_err:
                    logger.error(f"[AI Analysis Error] Provider {req.provider} call failed: {call_err}. Falling back to simulation.")
                    import random
                    headline_lower = req.headline.lower()
                    is_geopolitical = any(x in headline_lower for x in ["war", "strike", "attack", "kill", "protest", "military", "border", "missile", "died", "bridge", "disaster", "hunger"])
                    is_macro = any(x in headline_lower for x in ["cpi", "nfp", "fed", "rate", "inflation", "gdp", "job", "interest"])
                    
                    sentiment = "NEUTRAL"
                    if any(x in headline_lower for x in ["kill", "die", "attack", "bomb", "crisis", "disaster"]):
                        sentiment = "CRITICAL"
                    elif any(x in headline_lower for x in ["protest", "clash", "fell", "drop", "warn", "hunger", "sparks"]):
                        sentiment = "NEGATIVE"
                    
                    decision = "HOLD"
                    confidence = 25
                    
                    if sentiment == "CRITICAL":
                        decision = "SHORT"
                        confidence = random.randint(35, 45)
                    elif sentiment == "NEGATIVE":
                        decision = "SHORT"
                        confidence = random.randint(30, 38)
                        
                    simulated_json = {
                        "isGeopolitical": is_geopolitical,
                        "isMacro": is_macro,
                        "crisisKeywords": [w[:10] for w in headline_lower.split() if len(w) > 4][:3],
                        "sentiment": sentiment,
                        "impactScore": 45 if sentiment == "NEGATIVE" else (85 if sentiment == "CRITICAL" else 15),
                        "macroDetails": {
                            "eventName": "N/A" if not is_macro else "Macro Indicator",
                            "actualValue": "N/A",
                            "forecastValue": "N/A",
                            "deviation": 0.0,
                            "usdStrengthened": False
                        },
                        "assetsImpact": [
                            {"symbol": "BTC", "direction": "DOWN" if sentiment in ["CRITICAL", "NEGATIVE"] else "NEUTRAL", "percentage": -0.12 if sentiment in ["CRITICAL", "NEGATIVE"] else 0.0},
                            {"symbol": "SOL", "direction": "DOWN" if sentiment in ["CRITICAL", "NEGATIVE"] else "NEUTRAL", "percentage": -0.15 if sentiment in ["CRITICAL", "NEGATIVE"] else 0.0},
                            {"symbol": "XAU", "direction": "UP" if is_geopolitical else "NEUTRAL", "percentage": 0.08 if is_geopolitical else 0.0},
                            {"symbol": "DXY", "direction": "NEUTRAL", "percentage": 0.0}
                        ],
                        "analysisSummary": f"[SIMULATED FALLBACK] Berita '{req.headline}' dianalisis dengan sentimen {sentiment}. Mengingat keterbatasan data/koneksi provider {req.provider}, sistem menggunakan estimasi statistik.",
                        "tradeDecision": {
                            "decision": decision,
                            "targetAsset": target_asset,
                            "confidence": confidence,
                            "recommendedLeverage": "5x" if decision != "HOLD" else "N/A",
                            "recommendedStopLoss": "2.5%" if decision != "HOLD" else "N/A",
                            "strategyReasoning": f"Reaksi simulasi netral/defensif berdasarkan kategori sentimen {sentiment} dan batasan risiko bot."
                        }
                    }
                    response_text = json.dumps(simulated_json)
                
                if len(llm_response_cache) >= 100:
                    oldest_key = next(iter(llm_response_cache))
                    llm_response_cache.pop(oldest_key, None)
                llm_response_cache[cache_key] = response_text

        parsed_analysis = clean_and_parse_json(response_text)

        ai_decision = parsed_analysis.get("tradeDecision", {})
        ai_confidence = ai_decision.get("confidence", 0)
        if ai_confidence < confidence_threshold:
            ai_decision["decision"] = "HOLD"
            parsed_analysis["tradeDecision"] = ai_decision
            
        target_asset = ai_decision.get("targetAsset", "BTC").upper()
        llm_decision = ai_decision.get("decision", "HOLD").upper()
        
        crypto_assets = ["BTC", "ETH", "SOL", "BNB"]
        veto_active = False
        veto_reason = ""
        is_ood = False
        ood_violations = []
        ml_prediction = 0
        ml_confidence = 0.0
        meta_p_win = 0.0
        meta_approved = True
        meta_evaluated = False

        # Initialize bypass_veto default for scope safety in nested blocks
        strategy_name = bot_settings.get("strategy", "CONSERVATIVE").upper()
        bypass_veto = strategy_name in ["AGGRESSIVE", "SCALPING", "HEDGING"]

        if llm_decision in ["LONG", "SHORT"]:
            if target_asset not in crypto_assets:
                logger.info(f"[Veto Gate] Asset {target_asset} not supported by ML pipeline")
                veto_active = True
                veto_reason = f"Asset {target_asset} not supported by ML pipeline — forcing HOLD for safety"
                if not bypass_veto:
                    logger.info(f"[Veto Gate] Forcing HOLD for safety")
                    ai_decision["decision"] = "HOLD"
                    parsed_analysis["tradeDecision"] = ai_decision
            else:
                try:
                    from backend.services.ml.inference import fetch_recent_candles, predict_live_with_gate
                    
                    df_recent = await fetch_recent_candles(target_asset, count=120, interval="5m")
                    model_type = bot_settings.get("modelType", config.get("mlModelType", "xgboost"))
                    resample_min = bot_settings.get("timeframeMinutes", 5)
                    
                    ml_prediction, ml_confidence, is_ood, ood_violations, meta_p_win, meta_approved, meta_evaluated = predict_live_with_gate(
                        df_recent, model_type=model_type, resample_minutes=resample_min
                    )
                
                    logger.info(f"[Decision Fusion] LLM proposed {llm_decision} on {target_asset}.")
                    logger.info(f"[Decision Fusion] ML predict: {ml_prediction} (confidence: {ml_confidence:.4f}), is_ood: {is_ood}")
                    logger.info(f"[Decision Fusion] Meta-model: P(win)={meta_p_win if meta_p_win is not None else 0.0:.4f}, Approved={meta_approved}, Evaluated={meta_evaluated}")
                    
                    ml_weight = bot_settings.get("mlWeight", 0.5)
                    llm_weight = bot_settings.get("llmWeight", 0.5)
                    
                    if is_ood:
                        logger.info(f"[Decision Fusion] OOD Guard active. Market anomaly detected.")
                        veto_active = True
                        veto_reason = f"OOD Guard Active ({len(ood_violations)} violations) - conservative HOLD triggered."
                        if not bypass_veto:
                            logger.info(f"[Decision Fusion] Overriding LLM decision to HOLD out of caution.")
                            ai_decision["decision"] = "HOLD"
                            parsed_analysis["tradeDecision"] = ai_decision
                    else:
                        llm_conf = float(ai_decision.get("confidence", 50)) / 100.0
                        if llm_decision == "SHORT": llm_conf = -llm_conf
                        elif llm_decision == "HOLD": llm_conf = 0.0
                        
                        ml_conf = float(ml_confidence)
                        if ml_prediction == -1: ml_conf = -ml_conf
                        elif ml_prediction == 0: ml_conf = 0.0
                        
                        # Fusion score calculation
                        fusion_score = (llm_conf * llm_weight) + (ml_conf * ml_weight)
                        logger.info(f"[Decision Fusion] Fusion Score: {fusion_score:.4f} (LLM: {llm_conf:.2f}*{llm_weight}, ML: {ml_conf:.2f}*{ml_weight})")
                        
                        decision_threshold = 0.15
                        if fusion_score > decision_threshold:
                            final_decision = "LONG"
                        elif fusion_score < -decision_threshold:
                            final_decision = "SHORT"
                        else:
                            final_decision = "HOLD"
                            
                        max_w = max(llm_weight, ml_weight) if max(llm_weight, ml_weight) > 0 else 1.0
                        fused_confidence_pct = int(min(100, abs(fusion_score) * 100 * (1.0 / max_w)))
                        
                        if not bypass_veto:
                            if final_decision != llm_decision:
                                logger.info(f"[Decision Fusion] Overriding LLM {llm_decision} -> {final_decision} (Score: {fusion_score:.2f})")
                                veto_active = True
                                veto_reason = f"Decision Fusion resolved to {final_decision} (Score: {fusion_score:.2f})"
                            
                            ai_decision["decision"] = final_decision
                            ai_decision["confidence"] = fused_confidence_pct
                            parsed_analysis["tradeDecision"] = ai_decision
                        else:
                            logger.info(f"[Decision Fusion] Strategy is {strategy_name} — bypassing fusion override.")
                except Exception as ml_err:
                    logger.error(f"[Veto Gate] Error running ML confirmation/veto gate: {ml_err}.")
                    veto_active = True
                    veto_reason = f"ML gate error: {str(ml_err)}"
                    meta_p_win = None
                    meta_approved = False
                    meta_evaluated = False
                    if not bypass_veto:
                        logger.info(f"[Veto Gate] Forcing HOLD for safety.")
                        ai_decision["decision"] = "HOLD"
                        parsed_analysis["tradeDecision"] = ai_decision
                
        parsed_analysis["vetoGate"] = {
            "vetoActive": veto_active,
            "vetoReason": veto_reason,
            "isOod": is_ood,
            "oodViolations": ood_violations,
            "mlPrediction": ml_prediction,
            "mlConfidence": ml_confidence,
            "metaPWin": meta_p_win,
            "metaApproved": meta_approved,
            "metaModelEvaluated": meta_evaluated
        }

        # Add Markov Regime Gate check (In addition to existing OOD/ML checks)
        try:
            # Import HMM tools from services
            from backend.services.markov_regime import get_cached_markov_analysis
            
            # Fetch daily candles & run Markov analysis with non-blocking 1-hour cache
            target_ticker = f"{target_asset}-USD"
            markov_res = await get_cached_markov_analysis(target_ticker, years=5, window=20, threshold=0.05, min_train=252, hmm=False)
            
            current_regime = markov_res.get("current_regime", "Sideways")
            stationary_bear = markov_res.get("stationary_distribution", {}).get("bear", 0.0)
            markov_signal = markov_res.get("signal", 0.0)
            
            # If Bear or Sideways with >= 70% stationary probability or current state is Bear, veto directional trades
            # 70% threshold is conservative. Note: Bear regime state is highly persistence (Diagonal state P[0,0] is sticky).
            markov_threshold = 0.70
            
            parsed_analysis["vetoGate"]["markovRegime"] = current_regime
            parsed_analysis["vetoGate"]["markovConfidence"] = float(stationary_bear)
            
            # Check conditions for gating
            is_markov_bearish = current_regime == "Bear" or stationary_bear >= markov_threshold
            if is_markov_bearish and llm_decision in ["LONG", "SHORT"] and not bypass_veto:
                veto_active = True
                veto_reason = f"Markov Regime Gate Active (Regime: {current_regime}, Bear probability: {stationary_bear:.2%}) - conservative HOLD triggered."
                
                # Force override decision to HOLD
                ai_decision["decision"] = "HOLD"
                parsed_analysis["tradeDecision"] = ai_decision
                parsed_analysis["vetoGate"]["vetoActive"] = veto_active
                parsed_analysis["vetoGate"]["vetoReason"] = veto_reason
                logger.info(f"[Markov Gate] Overriding LLM decision to HOLD out of caution: {veto_reason}")
        except Exception as markov_err:
            logger.error(f"[Markov Gate] Error running Markov regime validation: {markov_err}")
            # Do not force lock on markov error to degrade gracefully, but log it
            parsed_analysis["vetoGate"]["markovRegime"] = "Error"
            parsed_analysis["vetoGate"]["markovConfidence"] = 0.0

        is_geopolitical = bool(parsed_analysis.get("isGeopolitical"))
        is_macro = bool(parsed_analysis.get("isMacro"))
        
        usd_strengthened = False
        if is_macro and parsed_analysis.get("macroDetails"):
            usd_strengthened = bool(parsed_analysis["macroDetails"].get("usdStrengthened"))
            
        is_triggered_short = is_geopolitical or (is_macro and usd_strengthened)
        is_triggered_gold = is_geopolitical

        generated_event = {
            "id": f"news-{int(time.time() * 1000)}",
            "time": time.strftime("%H:%M:%S"),
            "headline": req.headline,
            "category": "GEOPOLITICS" if is_geopolitical else ("MACRO" if is_macro else "GENERAL"),
            "impact": "CRITICAL" if parsed_analysis.get("sentiment") == "CRITICAL" else ("NEGATIVE" if parsed_analysis.get("sentiment") == "NEGATIVE" else "NEUTRAL"),
            "source": req.source or f"AI Analyst ({req.provider.upper()})",
            "details": parsed_analysis.get("analysisSummary", "Hasil analisis kecerdasan buatan."),
            "forecast": getattr(req, "forecast", ""),
            "previous": getattr(req, "previous", ""),
            "isTriggeredShort": is_triggered_short,
            "isTriggeredGold": is_triggered_gold,
            "summaryId": f"AI Terminal ({req.provider.upper()}): Crisis {parsed_analysis.get('crisisKeywords', [])} detected. Short signal: {'ACTIVE' if is_triggered_short else 'INACTIVE'}."
        }

        if req.source != "System Indicator":
            async with news_feed_lock:
                news_feed.insert(0, generated_event)
                if len(news_feed) > 50:
                    news_feed.pop()

        if is_geopolitical:
            current_panic.update({ "active": True, "type": "GEOPOLITICS", "title": req.headline, "timeLeft": 15 })
        elif is_macro and usd_strengthened:
            current_panic.update({ "active": True, "type": "MACRO", "title": req.headline, "timeLeft": 15 })

        try:
            async with db_lock:
                db = await read_database_async()
                if "savedAnalyses" not in db:
                    db["savedAnalyses"] = []
                db["savedAnalyses"].insert(0, {
                    "id": generated_event["id"],
                    "timestamp": int(time.time() * 1000),
                    "headline": req.headline,
                    "source": generated_event["source"],
                    "analysis": parsed_analysis,
                    "event": generated_event,
                    "marketMetrics": {
                        "volatilities": [{ "symbol": a["symbol"], "pctVol": calculate_asset_volatility(a["history"])["pctVolatility"] } for a in assets],
                        "fng": int(fng_cache["value"]),
                        "newsSentimentScore": news_sentiment["score"]
                    }
                })
                db["savedAnalyses"] = db["savedAnalyses"][:50]
                await write_database_async(db)
        except Exception as db_err:
            logger.error(f"[DATABASE] Failed to save analysis: {db_err}")

        return {
            "fallback": False,
            "provider": req.provider,
            "model": used_model,
            "analysis": parsed_analysis,
            "event": generated_event
        }
    except Exception as e:
        logger.error(f"Error in AI analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze with {req.provider}: {str(e)}")


@router.post("/api/gemini/analyze")
async def analyze_gemini(req: AIAnalyzeRequest):
    req.provider = "gemini"
    return await analyze_ai(req)


@router.post("/api/confidence-scorer/evaluate")
async def evaluate_confidence(req: EvaluateRequest):
    target_symbol = req.symbol or "BTC"
    asset_obj = next((a for a in assets if a["symbol"] == target_symbol), None)
    
    if not asset_obj:
        raise HTTPException(status_code=404, detail=f"Asset with symbol {target_symbol} not found")

    history = asset_obj.get("history", [])
    atr = 0.0
    pct_atr = 0.0
    if len(history) >= 2:
        trs = []
        for i in range(1, len(history)):
            prev_close = history[i-1]
            close = history[i]
            high = max(close, prev_close) * 1.0015
            low = min(close, prev_close) * 0.9985
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)
        period = min(14, len(trs))
        last_trs = trs[-period:]
        atr = sum(last_trs) / len(last_trs)
        current_price = history[-1] if history else 1.0
        pct_atr = (atr / current_price) * 100

    sentiment_result = analyze_sentiment(req.headline)
    raw_score = sentiment_result["score"]
    sentiment_strength = min(100, abs(raw_score) * 15 + 20)

    normalized_vol = min(100.0, (pct_atr / 1.2) * 100.0)

    confidence_percentage = round(0.6 * sentiment_strength + 0.4 * normalized_vol)
    confidence_percentage = max(10, min(98, confidence_percentage))

    recommended_action = "HOLD"
    if raw_score < 0:
        recommended_action = "SHORT"
    elif raw_score > 0:
        recommended_action = "LONG"

    leverage_val = "10x" if pct_atr > 0.8 else "5x"
    stop_loss_pct = f"{round(pct_atr * 1.5, 1)}%"

    return {
        "headline": req.headline,
        "symbol": target_symbol,
        "sentiment": {
            "score": raw_score,
            "comparative": sentiment_result["comparative"],
            "positiveWords": sentiment_result["positive"],
            "negativeWords": sentiment_result["negative"],
            "tokens": sentiment_result["tokens"]
        },
        "volatility": {
            "atr": round(atr, 4),
            "pctAtr": round(pct_atr, 3),
            "normalizedVol": round(normalized_vol, 2)
        },
        "scorer": {
            "sentimentWeight": 60,
            "volatilityWeight": 40,
            "confidence": confidence_percentage
        },
        "setup": {
            "action": recommended_action,
            "targetAsset": target_symbol,
            "leverage": "N/A" if recommended_action == "HOLD" else leverage_val,
            "stopLoss": "N/A" if recommended_action == "HOLD" else stop_loss_pct,
            "reasoning": f"Berdasarkan analisis sentiment (Score: {raw_score}) dan volatilitas ATR real-time ({pct_atr:.3f}%). Sentimen pasar {'NEGATIF' if raw_score < 0 else 'POSITIF' if raw_score > 0 else 'NETRAL'} dengan tingkat volatilitas ATR yang {'TINGGI' if pct_atr > 0.8 else 'RENDAH'}."
        }
    }
