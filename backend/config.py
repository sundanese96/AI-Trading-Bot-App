import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database path
DB_PATH = BASE_DIR / "database.json"

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CUSTOM_AI_KEY = os.getenv("CUSTOM_AI_KEY", "")
CUSTOM_AI_URL = os.getenv("CUSTOM_AI_URL", "")
CUSTOM_AI_MODEL = os.getenv("CUSTOM_AI_MODEL", "")

# Server settings
PORT = int(os.getenv("PORT", 3000))
HOST = "0.0.0.0"

# Security Settings
VERIFY_SSL = os.getenv("VERIFY_SSL", "True").lower() == "true"

# Dashboard Authentication Settings
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")
