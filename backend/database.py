import json
import os
from cryptography.fernet import Fernet
from backend.config import DB_PATH

# Generate or load encryption key
KEY_PATH = DB_PATH.parent / ".enc_key"
BACKUP_KEY_PATH = DB_PATH.parent / ".enc_key_backup"

if not os.path.exists(KEY_PATH):
    # If backup exists, restore it
    if os.path.exists(BACKUP_KEY_PATH):
        import shutil
        shutil.copy(BACKUP_KEY_PATH, KEY_PATH)
        with open(KEY_PATH, "rb") as f:
            key = f.read()
    else:
        if os.path.exists(DB_PATH):
            print("[WARNING] Generating NEW encryption key while database already exists. Old encrypted API keys may be lost!")
            
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        # Create backup
        with open(BACKUP_KEY_PATH, "wb") as f:
            f.write(key)
else:
    with open(KEY_PATH, "rb") as f:
        key = f.read()
    # Ensure backup exists
    if not os.path.exists(BACKUP_KEY_PATH):
        with open(BACKUP_KEY_PATH, "wb") as f:
            f.write(key)

cipher_suite = Fernet(key)

def encrypt_text(text: str) -> str:
    if not text:
        return ""
    return cipher_suite.encrypt(text.encode("utf-8")).decode("utf-8")

def decrypt_text(encrypted_text: str) -> str:
    if not encrypted_text:
        return ""
    try:
        return cipher_suite.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
    except Exception:
        # Fallback if text is not encrypted
        return encrypted_text

import asyncio

db_lock = asyncio.Lock()

def read_database():
    try:
        if not os.path.exists(DB_PATH):
            initial_db = {
                "savedAnalyses": [], 
                "savedTrades": [], 
                "aiConfig": {
                    "provider": "gemini",
                    "customUrl": "",
                    "customKey": "",
                    "customModel": "",
                    "binanceApiKey": "",
                    "binanceApiSecret": "",
                    "dryRun": True,
                    "maxDailyLoss": 5.0,
                    "maxTradesPerDay": 5,
                    "confidenceThreshold": 75,
                    "telegramBotToken": "",
                    "telegramChatId": "",
                    "isLocked": False
                },
                "dailyStats": {
                    "date": "",
                    "tradeCount": 0,
                    "dailyLoss": 0.0,
                    "dailyPnl": 0.0
                },
                "processedTradeIds": []
            }
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(initial_db, f, indent=2)
            return initial_db
        with open(DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            # Ensure default keys exist
            if "aiConfig" not in db:
                db["aiConfig"] = {}
            if "dailyStats" not in db:
                db["dailyStats"] = {
                    "date": "",
                    "tradeCount": 0,
                    "dailyLoss": 0.0,
                    "dailyPnl": 0.0
                }
            if "processedTradeIds" not in db:
                db["processedTradeIds"] = []
            # Set defaults for config
            config = db["aiConfig"]
            if "dryRun" not in config:
                config["dryRun"] = True
            if "maxDailyLoss" not in config:
                config["maxDailyLoss"] = 5.0
            if "maxTradesPerDay" not in config:
                config["maxTradesPerDay"] = 5
            if "confidenceThreshold" not in config:
                config["confidenceThreshold"] = 75
            if "isLocked" not in config:
                config["isLocked"] = False
            if "multiAssetMode" not in config:
                config["multiAssetMode"] = False
            if "vetoGateMode" not in config:
                config["vetoGateMode"] = "AUTO"
            return db
    except Exception as e:
        print(f"[DATABASE] Error reading database.json: {e}")
        return {"savedAnalyses": [], "savedTrades": [], "aiConfig": {}, "dailyStats": {}, "processedTradeIds": []}

def write_database(data):
    try:
        temp_file = str(DB_PATH) + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        import os
        os.replace(temp_file, DB_PATH)
    except Exception as e:
        print(f"[DATABASE] Error writing database.json: {e}")

async def read_database_async():
    return await asyncio.to_thread(read_database)

async def write_database_async(data):
    await asyncio.to_thread(write_database, data)

async def save_ai_config(config: dict):
    async with db_lock:
        db = await read_database_async()
        
        # Encrypt sensitive API keys before saving
        encrypted_config = dict(config)
        if "customKey" in encrypted_config:
            encrypted_config["customKey"] = encrypt_text(encrypted_config["customKey"])
        if "binanceApiKey" in encrypted_config:
            encrypted_config["binanceApiKey"] = encrypt_text(encrypted_config["binanceApiKey"])
        if "binanceApiSecret" in encrypted_config:
            encrypted_config["binanceApiSecret"] = encrypt_text(encrypted_config["binanceApiSecret"])
        if "telegramBotToken" in encrypted_config:
            encrypted_config["telegramBotToken"] = encrypt_text(encrypted_config["telegramBotToken"])
            
        if "aiConfig" not in db:
            db["aiConfig"] = {}
        db["aiConfig"].update(encrypted_config)
        await write_database_async(db)

async def load_ai_config() -> dict:
    async with db_lock:
        db = await read_database_async()
        config = db.get("aiConfig", {})
        
        # Decrypt API keys after loading
        decrypted_config = dict(config)
        if "customKey" in decrypted_config and decrypted_config["customKey"]:
            decrypted_config["customKey"] = decrypt_text(decrypted_config["customKey"])
        if "binanceApiKey" in decrypted_config and decrypted_config["binanceApiKey"]:
            decrypted_config["binanceApiKey"] = decrypt_text(decrypted_config["binanceApiKey"])
        if "binanceApiSecret" in decrypted_config and decrypted_config["binanceApiSecret"]:
            decrypted_config["binanceApiSecret"] = decrypt_text(decrypted_config["binanceApiSecret"])
        if "telegramBotToken" in decrypted_config and decrypted_config["telegramBotToken"]:
            decrypted_config["telegramBotToken"] = decrypt_text(decrypted_config["telegramBotToken"])
            
        return decrypted_config

async def get_daily_stats() -> dict:
    import time
    import datetime
    async with db_lock:
        db = await read_database_async()
        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - 24 * 60 * 60 * 1000
        
        if "pnlLog" not in db:
            db["pnlLog"] = []
            
        # Prune transactions older than 24 hours
        db["pnlLog"] = [tx for tx in db["pnlLog"] if tx["timestamp"] >= cutoff_ms]
        
        rolling_txs = db["pnlLog"]
        trade_count = len(rolling_txs)
        daily_pnl = sum(tx["pnl"] for tx in rolling_txs)
        daily_loss = sum(abs(tx["pnl"]) for tx in rolling_txs if tx["pnl"] < 0)
        
        today = datetime.date.today().isoformat()
        stats = {
            "date": today,
            "tradeCount": trade_count,
            "dailyLoss": round(daily_loss, 2),
            "dailyPnl": round(daily_pnl, 2)
        }
        db["dailyStats"] = stats
        await write_database_async(db)
        return stats

async def lock_bot():
    async with db_lock:
        db = await read_database_async()
        if "aiConfig" not in db:
            db["aiConfig"] = {}
        db["aiConfig"]["isLocked"] = True
        await write_database_async(db)

async def unlock_bot():
    async with db_lock:
        db = await read_database_async()
        if "aiConfig" not in db:
            db["aiConfig"] = {}
        db["aiConfig"]["isLocked"] = False
        await write_database_async(db)

async def update_daily_stats(pnl: float):
    import time
    import datetime
    async with db_lock:
        db = await read_database_async()
        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - 24 * 60 * 60 * 1000
        
        if "pnlLog" not in db:
            db["pnlLog"] = []
            
        # Append new transaction
        db["pnlLog"].append({
            "timestamp": now_ms,
            "pnl": pnl
        })
        
        # Prune transactions older than 24 hours
        db["pnlLog"] = [tx for tx in db["pnlLog"] if tx["timestamp"] >= cutoff_ms]
        
        rolling_txs = db["pnlLog"]
        trade_count = len(rolling_txs)
        daily_pnl = sum(tx["pnl"] for tx in rolling_txs)
        daily_loss = sum(abs(tx["pnl"]) for tx in rolling_txs if tx["pnl"] < 0)
        
        today = datetime.date.today().isoformat()
        stats = {
            "date": today,
            "tradeCount": trade_count,
            "dailyLoss": round(daily_loss, 2),
            "dailyPnl": round(daily_pnl, 2)
        }
        db["dailyStats"] = stats
        await write_database_async(db)

async def is_trade_processed(trade_id: str) -> bool:
    async with db_lock:
        db = await read_database_async()
        processed_ids = db.get("processedTradeIds", [])
        return str(trade_id) in processed_ids

async def mark_trade_as_processed(trade_id: str):
    async with db_lock:
        db = await read_database_async()
        if "processedTradeIds" not in db:
            db["processedTradeIds"] = []
        db["processedTradeIds"].append(str(trade_id))
        # Keep list size reasonable (last 1000 trades)
        db["processedTradeIds"] = db["processedTradeIds"][-1000:]
        await write_database_async(db)
