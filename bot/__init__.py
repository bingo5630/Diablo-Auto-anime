# bot/__init__.py
from dotenv import load_dotenv
from os import getenv

load_dotenv()  # ✅ MUST BE FIRST
print("[DEBUG] API_ID from .env:", getenv("API_ID"))

__version__ = "1.0.0"  # Optional: version info
