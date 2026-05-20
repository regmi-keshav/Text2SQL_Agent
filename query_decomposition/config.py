import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.0-mini").strip()

if not GEMINI_API_KEY:
    raise EnvironmentError(
        "Missing GEMINI_API_KEY in .env. Set GEMINI_API_KEY=<your_api_key> in the repository root .env file."
    )
