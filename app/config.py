from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def env(name: str, default: str = '') -> str:
    return os.getenv(name, default).strip()


def enabled(name: str, default: bool = False) -> bool:
    return env(name, 'true' if default else 'false').lower() in ('1', 'true', 'yes', 'on')


DATA = ROOT / 'data'
DOCUMENTS = DATA / 'documents'
AUDIO = DATA / 'audio'
UPLOADS = DATA / 'uploads'
CACHE = DATA / 'cache'
DB_FILE = DATA / 'sahayak.db'
for directory in (DATA, DOCUMENTS, AUDIO, UPLOADS, CACHE):
    directory.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = env('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
OLLAMA_MODEL = env('OLLAMA_MODEL', 'llama3.2:latest')
VISION_MODEL = env('VISION_MODEL', 'qwen2.5vl:3b')
GEMINI_KEY = env('GEMINI_API_KEY')
GEMINI_MODEL = env('GEMINI_MODEL', 'gemini-3.5-flash-lite')
USE_GEMINI = enabled('USE_GEMINI', default=bool(GEMINI_KEY))
USE_LLM_VERIFIER = enabled('USE_LLM_VERIFIER')
DATA_GOV_KEY = env('DATA_GOV_API_KEY')
DATA_GOV_RESOURCE = env('DATA_GOV_RESOURCE_ID', '9ef84268-d588-465a-a308-a864a43d0070')
CEDA_KEY = env('CEDA_API_KEY')
TELEGRAM_TOKEN = env('TELEGRAM_BOT_TOKEN')
USER_AGENT = env('OSM_USER_AGENT', 'GramSahayak/1.0 (non-commercial agricultural assistant)')
RAG_MODEL = env('RAG_MODEL', 'intfloat/multilingual-e5-small')
TTS_BACKEND = env('TTS_BACKEND', 'gtts').lower()
