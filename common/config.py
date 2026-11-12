"""Configuration: reads environment variables (.env) and data paths."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "").strip()

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in .env (see .env.example).")
if not OPENAI_MODEL:
    raise RuntimeError("OPENAI_MODEL is not set in .env (see .env.example).")
