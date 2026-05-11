"""Shared utilities, database connections, and client instances."""
import os
import re
import logging
import uuid
import requests
import base64
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from emergentintegrations.llm.openai import OpenAISpeechToText
from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
from elevenlabs import ElevenLabs as ElevenLabsClient
from elevenlabs import VoiceSettings

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Database
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Keys
EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
ELEVENLABS_KEY = os.environ.get('ELEVENLABS_API_KEY', '')

# Clients
eleven_client = ElevenLabsClient(api_key=ELEVENLABS_KEY) if ELEVENLABS_KEY else None
stt_client = OpenAISpeechToText(api_key=EMERGENT_KEY) if EMERGENT_KEY else None
openai_image_gen = OpenAIImageGeneration(api_key=EMERGENT_KEY) if EMERGENT_KEY else None

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ----- Object Storage -----
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "hermes-nexus"
storage_key = None

def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    logger.info("Object storage initialized")
    return storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# ----- Utilities -----

def now_iso():
    return datetime.now(timezone.utc).isoformat()

async def log_operation(action: str, agent: str = "", details: str = "", status: str = "SUCCESS"):
    doc = {
        "id": str(uuid.uuid4()),
        "action": action,
        "agent": agent,
        "details": details,
        "status": status,
        "timestamp": now_iso()
    }
    await db.operations.insert_one(doc)
    return doc
