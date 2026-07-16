import httpx
import os
from backend.database import load_ai_config

# Load Telegram credentials from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

async def send_telegram_alert(message: str):
    """Sends a real-time alert message to the configured Telegram chat."""
    config = await load_ai_config()
    token = config.get("telegramBotToken", TELEGRAM_BOT_TOKEN)
    chat_id = config.get("telegramChatId", TELEGRAM_CHAT_ID)
    
    if not token or not chat_id:
        print(f"[Telegram Alert] Credentials missing. Alert not sent: {message}")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"⚠️ [AI Trading Bot Alert]\n\n{message}",
        "parse_mode": "Markdown"
    }
    
    try:
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.post(url, json=payload, timeout=10.0)
            if res.status_code != 200:
                print(f"[Telegram Alert] Failed to send alert: {res.text}")
            else:
                print(f"[Telegram Alert] Alert sent successfully.")
    except Exception as e:
        print(f"[Telegram Alert] Exception occurred: {str(e)}")
