import json
from fastapi import APIRouter, Request, HTTPException
from backend.core.logger import logger
from backend.database import load_ai_config, read_database_async
from backend.services.ai import call_gemini, call_openai, call_anthropic, call_custom, call_semburat_gateway, clean_and_parse_json
from backend.config import GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, CUSTOM_AI_KEY

router = APIRouter()

@router.post("/api/ai-bot/optimize-settings")
async def optimize_settings_endpoint(request: Request):
    """
    Asks the LLM model to analyze the current bot settings, news, and market context
    to recommend optimized trading parameters (returns JSON containing updated settings).
    """
    try:
        body = await request.json()
        current_settings = body.get("settings", {})
        
        # Load central system config (check if it is simulated or real Binance mode)
        config = await load_ai_config() or {}
        dry_run = config.get("dryRun", True)
        
        # Detect active Binance balance (mock or real USD depending on dryRun)
        db = await read_database_async()
        sim_balance = 100000.0  # default
        if "portfolio" in db and isinstance(db["portfolio"], dict):
            sim_balance = db["portfolio"].get("balanceUSD", 100000.0)
            
        is_simulated_mode = dry_run
        account_balance_str = f"${sim_balance:,.2f} USDT (Simulated)" if is_simulated_mode else "N/A USDT (Real Binance Mode — Balance protected by keys)"
        
        # Fetch current real-time market overview
        from backend.services.market import assets
        market_stats = []
        for a in assets:
            market_stats.append(f"- {a['symbol']}: Price ${a['price']}, 24h Change {a['change24h']}%")
        market_overview = "\n".join(market_stats)
        
        # Fetch news context
        from backend.services.news import news_feed
        recent_headlines = []
        for n in news_feed[:3]:
            recent_headlines.append(f"- [{n['time']}] {n['headline']} ({n['category']})")
        news_context = "\n".join(recent_headlines)
        
        # Define LLM instructions
        system_instruction = """You are a senior quantitative risk manager. Your job is to analyze the bot's current parameter configuration, market conditions, recent news events, and model benchmark test results to recommend optimized trading settings.
You must return your output ONLY as a valid JSON object matching the exact keys of the input configuration settings. Do not write any preamble, explanation, or markdown block. Return ONLY the JSON object.

Keys to include in output JSON:
{
  "leverage": integer (1 to 10),
  "llmWeight": float (0.0 to 1.0),
  "mlWeight": float (0.0 to 1.0, must sum to 1.0 with llmWeight),
  "minConfidence": integer (20 to 90),
  "stopLossPct": float (0.5 to 3.0),
  "takeProfitPct": float (1.0 to 8.0),
  "trailingStopPct": float (0.1 to 2.5),
  "allocationPerTrade": number (50 to 5000),
  "sentimentThreshold": float (0.05 to 0.50),
  "riskLevel": "LOW" or "MEDIUM" or "HIGH",
  "tpMultiplier": float (0.5 to 2.5),
  "slMultiplier": float (0.5 to 2.5),
  "vetoGateMode": "ON" or "OFF" or "AUTO",
  "modelType": "xgboost" or "lightgbm" or "catboost",
  "timeframeMinutes": 5 or 15 or 60
}"""
        
        # Read the latest V2 benchmark results (Binary mode + Dynamic ATR Triple-Barrier)
        benchmark_results = "N/A"
        try:
            from backend.scratch.train_v2 import train_and_eval_binary_vs_multiclass
            import subprocess
            import sys
            
            # Run the V2 benchmark script and capture output
            result = subprocess.run(
                [sys.executable, "-c", """
import sys
sys.path.insert(0, '/media/sun/DATA/sentix-ai-crypto-simulator')
from backend.scratch.train_v2 import train_and_eval_binary_vs_multiclass
for tf in [5, 15, 60, 180]:
    train_and_eval_binary_vs_multiclass(tf)
"""],
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode == 0 and "ACCURACY" in result.stdout:
                benchmark_results = result.stdout
        except Exception as bench_err:
            logger.error(f"[AI Optimizer] Benchmark reading failed: {bench_err}")
            
        prompt = f"""=== CURRENT BOT SETTINGS ===
{json.dumps(current_settings, indent=2)}

=== ACTIVE ENVIRONMENT STATUS ===
- Mode: {"SIMULATION (Paper Trading)" if is_simulated_mode else "REAL TRADING (Binance Live)"}
- Account Balance: {account_balance_str}

=== RECENT NEWS HEADLINES ===
{news_context}

=== REAL-TIME CRYPTO MARKET OVERVIEW ===
{market_overview}

=== MACHINE LEARNING MODEL BENCHMARK RESULTS ===
{benchmark_results}

Based on the current volatility, sentiment, environment balance, and ML model accuracy/F1 performance benchmarks, recommend the optimal settings. Select the modelType and timeframeMinutes that have shown the highest accuracy/F1 and best P&L in the benchmark. If the market is neutral/sideways, suggest a conservative structure.
"""
        
        # Determine provider & model
        provider = config.get("provider", "gemini")
        used_model = "gemini-1.5-flash"
        
        api_key = ""
        if provider == "gemini":
            api_key = config.get("customKey") or GEMINI_API_KEY
            used_model = config.get("customModel") or "gemini-1.5-flash"
        elif provider == "openai":
            api_key = config.get("customKey") or OPENAI_API_KEY
            used_model = config.get("customModel") or "gpt-4o-mini"
        elif provider == "anthropic":
            api_key = config.get("customKey") or ANTHROPIC_API_KEY
            used_model = config.get("customModel") or "claude-3-5-sonnet-latest"
        elif provider == "custom":
            api_key = config.get("customKey") or CUSTOM_AI_KEY
            used_model = config.get("customModel") or "custom-model"
            
        has_no_key = not api_key or api_key in ["MY_GEMINI_API_KEY", "MY_OPENAI_API_KEY", "MY_ANTHROPIC_API_KEY"]
        use_fallback = has_no_key and (provider not in ["custom"] or not config.get("customUrl"))
        
        response_text = ""
        if use_fallback:
            # High-fidelity mock optimizer recommendation response
            print("[Optimizer AI] No API key, returning local high-fidelity fallback parameters.")
            fallback_settings = {
                "leverage": 5 if current_settings.get("riskLevel") == "LOW" else 8,
                "llmWeight": 0.35,
                "mlWeight": 0.65,
                "minConfidence": 45,
                "stopLossPct": 1.2,
                "takeProfitPct": 2.5,
                "trailingStopPct": 0.4,
                "allocationPerTrade": 500 if is_simulated_mode else 100,
                "sentimentThreshold": 0.20,
                "riskLevel": "MEDIUM",
                "tpMultiplier": 1.0,
                "slMultiplier": 1.0,
                "vetoGateMode": "AUTO"
            }
            return {"success": True, "optimizedSettings": fallback_settings, "message": "Fallback optimizer applied."}
            
        else:
            if provider == "gemini":
                response_text = await call_gemini(api_key, used_model, system_instruction, prompt)
            elif provider == "openai":
                response_text = await call_openai(api_key, used_model, system_instruction, prompt)
            elif provider == "anthropic":
                response_text = await call_anthropic(api_key, used_model, system_instruction, prompt)
            elif provider == "custom":
                response_text = await call_custom(api_key, config.get("customUrl", ""), used_model, system_instruction, prompt)
                
            optimized_data = clean_and_parse_json(response_text)
            
            # Merge with existing settings for keys we didn't update (e.g. strategy, symbol, enabled)
            merged_settings = dict(current_settings)
            merged_settings.update(optimized_data)
            
            return {
                "success": True, 
                "optimizedSettings": merged_settings,
                "message": f"Successfully optimized settings using {provider} model: {used_model}."
            }
            
    except Exception as e:
        logger.error(f"[AI Settings Optimizer] Error: {e}")
        return {"success": False, "message": str(e)}
