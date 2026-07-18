import httpx
import os
from backend.database import load_ai_config
from backend.config import VERIFY_SSL

# Load Telegram credentials from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def log_telegram_notification(recipient: str, message: str, status: str):
    try:
        from backend.sentix_adapter import sentix_state, _save_sentix_db
        import time
        from datetime import datetime
        log_entry = {
            "id": int(time.time() * 1000),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "TELEGRAM",
            "recipient": recipient,
            "message": message,
            "status": status.upper()
        }
        if "notificationLogs" not in sentix_state:
            sentix_state["notificationLogs"] = []
        sentix_state["notificationLogs"].append(log_entry)
        sentix_state["notificationLogs"] = sentix_state["notificationLogs"][-100:]
        _save_sentix_db()
    except Exception as e:
        print(f"[Telegram Alert Log] Failed to save log: {e}")

async def send_telegram_alert(message: str):
    """Sends a real-time alert message to the configured Telegram chat."""
    config = await load_ai_config()
    token = config.get("telegramBotToken") or config.get("telegramToken") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = config.get("telegramChatId") or os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Fallback to sentix_state
    if not token or not chat_id:
        try:
            from backend.sentix_adapter import sentix_state
            sentix_config = sentix_state.get("notificationSettings", {})
            if not token:
                token = sentix_config.get("telegramToken") or sentix_config.get("telegramBotToken", "")
            if not chat_id:
                chat_id = sentix_config.get("telegramChatId", "")
        except Exception:
            pass
            
    if not token or not chat_id:
        print(f"[Telegram Alert] Credentials missing. Alert not sent: {message}")
        log_telegram_notification("Unknown (Missing Credentials)", message, "FAILED")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"⚠️ [AI Trading Bot Alert]\n\n{message}",
        "parse_mode": "Markdown"
    }
    
    try:
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            res = await client.post(url, json=payload, timeout=10.0)
            if res.status_code != 200:
                print(f"[Telegram Alert] Failed to send alert: {res.text}")
                log_telegram_notification(chat_id, message, f"FAILED ({res.status_code})")
            else:
                print(f"[Telegram Alert] Alert sent successfully.")
                log_telegram_notification(chat_id, message, "SUCCESS")
    except Exception as e:
        print(f"[Telegram Alert] Exception occurred: {str(e)}")
        log_telegram_notification(chat_id, message, f"FAILED (Exception: {str(e)})")
