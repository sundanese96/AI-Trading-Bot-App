from backend.core.logger import logger
import os
import asyncio

# Force reload trigger comment

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import PORT, HOST
from backend.services import db_manager
from backend.services.market import (
    market_simulation_loop, real_prices_loop, fear_and_greed_loop
)
from backend.services.position_monitor import monitor_binance_positions_loop

from backend.trading.bot import ai_bot_automated_loop
from backend.trading.monitor import monitor_simulated_positions_loop
from backend.scrapers.news_scraper import news_scraper_loop


background_tasks = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database
    await db_manager.init_db()
    
    # Sync Sentix LLM Settings to database.json aiConfig at startup
    from backend.sentix_adapter import sentix_state
    from backend.database import save_ai_config
    llm_settings = sentix_state.get("llmSettings", {})
    if llm_settings:
        try:
            await save_ai_config({
                "provider": llm_settings.get("provider", "simulated"),
                "customUrl": llm_settings.get("baseUrl", ""),
                "customKey": llm_settings.get("apiKey", ""),
                "customModel": llm_settings.get("modelName", ""),
            })
            logger.info("[Startup] Successfully synced LLM settings from UI state to backend config.")
        except Exception as e:
            logger.error(f"[Startup] Failed to sync LLM settings: {e}")

    # Start background tasks
    global background_tasks
    sim_task = asyncio.create_task(market_simulation_loop())
    prices_task = asyncio.create_task(real_prices_loop())
    fng_task = asyncio.create_task(fear_and_greed_loop())
    scraper_task = asyncio.create_task(news_scraper_loop())
    ai_bot_task = asyncio.create_task(ai_bot_automated_loop())
    monitor_task = asyncio.create_task(monitor_binance_positions_loop())
    sim_monitor_task = asyncio.create_task(monitor_simulated_positions_loop())
    
    background_tasks.update([sim_task, prices_task, fng_task, scraper_task, ai_bot_task, monitor_task, sim_monitor_task])
    yield
    # Clean up background tasks
    sim_task.cancel()
    prices_task.cancel()
    fng_task.cancel()
    scraper_task.cancel()
    ai_bot_task.cancel()
    monitor_task.cancel()
    sim_monitor_task.cancel()
    try:
        await asyncio.gather(sim_task, prices_task, fng_task, scraper_task, monitor_task, sim_monitor_task, return_exceptions=True)
    except Exception:
        pass
    
    # Close shared AI HTTP client
    try:
        from backend.services.ai import _shared_client
        if _shared_client:
            await _shared_client.aclose()
    except Exception as e:
        logger.error(f"[Shutdown] Error closing AI client: {e}")

app = FastAPI(title="Sentix AI Trading Terminal", lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


from backend.api.auth import router as auth_router
app.include_router(auth_router)

from backend.api.market import router as market_router
app.include_router(market_router)

from backend.api.simulation import router as simulation_router
app.include_router(simulation_router)

from backend.api.trades import router as trades_router
app.include_router(trades_router)

# Register Sentix UI compatibility adapter routes (takes priority)
from backend.sentix_adapter import router as sentix_router
app.include_router(sentix_router)

# Register Live Trading router
from backend.live_trading.endpoints import router as live_trading_router
app.include_router(live_trading_router)

# --- NEW MODULAR ROUTERS ---
from backend.routes.ai import router as ai_router
app.include_router(ai_router)

from backend.routes.ml import router as ml_router
app.include_router(ml_router)

from backend.routes.news import router as news_router
app.include_router(news_router)

from backend.routes.trading import router as binance_trading_router
app.include_router(binance_trading_router)

from backend.routes.backtest import router as backtest_router
app.include_router(backtest_router)


# Serve static files from 'dist' directory if it exists
dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")
if os.path.exists(dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")
    
    @app.get("/{path_name:path}")
    async def serve_spa(path_name: str):
        if path_name.startswith("api"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = os.path.join(dist_dir, path_name)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        response = FileResponse(os.path.join(dist_dir, "index.html"))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

if __name__ == "__main__":
    import uvicorn
    should_reload = os.getenv("RELOAD", "false").lower() == "true"
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=should_reload, log_level="warning")
