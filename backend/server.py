from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage

import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ----- Pydantic Models -----

class AgentCreate(BaseModel):
    name: str
    description: str = ""
    operations: List[str] = []
    preferred_model: str = "gpt-5.2"
    preferred_provider: str = "openai"

class AgentUpdate(BaseModel):
    status: Optional[str] = None
    preferred_model: Optional[str] = None
    preferred_provider: Optional[str] = None

class DispatchCreate(BaseModel):
    agent_id: str
    prompt: str
    model_override: Optional[str] = None
    provider_override: Optional[str] = None

class NoteCreate(BaseModel):
    content: str
    tags: List[str] = []

class NoteUpdate(BaseModel):
    content: Optional[str] = None
    tags: Optional[List[str]] = None

class ForgeItemCreate(BaseModel):
    title: str
    type: str = "image"
    url: str = ""
    tags: List[str] = []
    source_agent: str = ""
    description: str = ""

class ModelConfig(BaseModel):
    provider: str
    model: str
    label: str

# ----- Utility -----

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

# ----- Agent Endpoints -----

@api_router.get("/agents")
async def get_agents():
    agents = await db.agents.find({}, {"_id": 0}).to_list(100)
    return agents

@api_router.post("/agents")
async def create_agent(agent: AgentCreate):
    doc = {
        "id": str(uuid.uuid4()),
        "name": agent.name,
        "description": agent.description,
        "operations": agent.operations,
        "preferred_model": agent.preferred_model,
        "preferred_provider": agent.preferred_provider,
        "status": "idle",
        "created_at": now_iso(),
        "last_active": now_iso(),
        "dispatch_count": 0
    }
    await db.agents.insert_one(doc)
    await log_operation("AGENT_REGISTERED", agent.name, f"Agent {agent.name} registered")
    doc.pop("_id", None)
    return doc

@api_router.patch("/agents/{agent_id}")
async def update_agent(agent_id: str, update: AgentUpdate):
    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_dict["last_active"] = now_iso()
    await db.agents.update_one({"id": agent_id}, {"$set": update_dict})
    agent = await db.agents.find_one({"id": agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

# ----- Dispatch & Transmission Endpoints -----

@api_router.post("/dispatches")
async def create_dispatch(dispatch: DispatchCreate):
    agent = await db.agents.find_one({"id": dispatch.agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    provider = dispatch.provider_override or agent.get("preferred_provider", "openai")
    model = dispatch.model_override or agent.get("preferred_model", "gpt-5.2")

    dispatch_doc = {
        "id": str(uuid.uuid4()),
        "agent_id": dispatch.agent_id,
        "agent_name": agent["name"],
        "prompt": dispatch.prompt,
        "model": model,
        "provider": provider,
        "status": "processing",
        "created_at": now_iso(),
        "response": None,
        "completed_at": None
    }
    await db.dispatches.insert_one(dispatch_doc)
    dispatch_doc.pop("_id", None)

    await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "busy", "last_active": now_iso()}, "$inc": {"dispatch_count": 1}})

    await log_operation("DISPATCH_SENT", agent["name"], f"Prompt: {dispatch.prompt[:80]}...", "PROCESSING")

    # Execute via LLM
    try:
        system_msg = f"You are {agent['name']}, an AI agent in the Hermes Command Nexus. {agent.get('description', '')}. You execute dispatched tasks with precision. Respond in a direct, technical manner befitting a command center operative."

        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"dispatch-{dispatch_doc['id']}",
            system_message=system_msg
        )
        chat.with_model(provider, model)

        user_message = UserMessage(text=dispatch.prompt)
        response_text = await chat.send_message(user_message)

        dispatch_doc["response"] = response_text
        dispatch_doc["status"] = "completed"
        dispatch_doc["completed_at"] = now_iso()

        await db.dispatches.update_one(
            {"id": dispatch_doc["id"]},
            {"$set": {"response": response_text, "status": "completed", "completed_at": now_iso()}}
        )
        await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "idle", "last_active": now_iso()}})
        await log_operation("TRANSMISSION_RECEIVED", agent["name"], f"Response received for dispatch {dispatch_doc['id']}", "SUCCESS")

    except Exception as e:
        logger.error(f"Dispatch execution error: {e}")
        dispatch_doc["response"] = f"[EXECUTION ERROR] {str(e)}"
        dispatch_doc["status"] = "failed"
        dispatch_doc["completed_at"] = now_iso()

        await db.dispatches.update_one(
            {"id": dispatch_doc["id"]},
            {"$set": {"response": dispatch_doc["response"], "status": "failed", "completed_at": now_iso()}}
        )
        await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "error", "last_active": now_iso()}})
        await log_operation("DISPATCH_FAILED", agent["name"], str(e), "ERROR")

    return dispatch_doc

@api_router.get("/dispatches")
async def get_dispatches(agent_id: Optional[str] = None, limit: int = 50):
    query = {}
    if agent_id:
        query["agent_id"] = agent_id
    dispatches = await db.dispatches.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return dispatches

@api_router.get("/dispatches/{dispatch_id}")
async def get_dispatch(dispatch_id: str):
    doc = await db.dispatches.find_one({"id": dispatch_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return doc

# ----- MemPalace Endpoints -----

@api_router.get("/mempalace/notes")
async def get_notes(search: Optional[str] = None):
    query = {}
    if search:
        query["$or"] = [
            {"content": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}}
        ]
    notes = await db.notes.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return notes

@api_router.post("/mempalace/notes")
async def create_note(note: NoteCreate):
    doc = {
        "id": str(uuid.uuid4()),
        "content": note.content,
        "tags": note.tags,
        "created_at": now_iso(),
        "updated_at": now_iso()
    }
    await db.notes.insert_one(doc)
    await log_operation("NOTE_CREATED", "MemPalace", f"Note created: {note.content[:50]}...")
    doc.pop("_id", None)
    return doc

@api_router.patch("/mempalace/notes/{note_id}")
async def update_note(note_id: str, update: NoteUpdate):
    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_dict["updated_at"] = now_iso()
    await db.notes.update_one({"id": note_id}, {"$set": update_dict})
    note = await db.notes.find_one({"id": note_id}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@api_router.delete("/mempalace/notes/{note_id}")
async def delete_note(note_id: str):
    result = await db.notes.delete_one({"id": note_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "deleted"}

@api_router.get("/mempalace/search")
async def search_mempalace(q: str):
    escaped = re.escape(q)
    regex = {"$regex": escaped, "$options": "i"}
    notes = await db.notes.find({"$or": [{"content": regex}, {"tags": regex}]}, {"_id": 0}).to_list(100)
    dispatches = await db.dispatches.find({"$or": [{"prompt": regex}, {"response": regex}]}, {"_id": 0}).to_list(100)
    return {"notes": notes, "transmissions": dispatches}

# ----- Forge Gallery Endpoints -----

@api_router.get("/forge")
async def get_forge_items(tag: Optional[str] = None):
    query = {}
    if tag:
        query["tags"] = tag
    items = await db.forge.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return items

@api_router.post("/forge")
async def create_forge_item(item: ForgeItemCreate):
    doc = {
        "id": str(uuid.uuid4()),
        "title": item.title,
        "type": item.type,
        "url": item.url,
        "tags": item.tags,
        "source_agent": item.source_agent,
        "description": item.description,
        "created_at": now_iso()
    }
    await db.forge.insert_one(doc)
    await log_operation("FORGE_ITEM_ADDED", item.source_agent or "Manual", f"Added: {item.title}")
    doc.pop("_id", None)
    return doc

@api_router.delete("/forge/{item_id}")
async def delete_forge_item(item_id: str):
    result = await db.forge.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "deleted"}

# ----- Operations Log -----

@api_router.get("/operations")
async def get_operations(limit: int = 100):
    ops = await db.operations.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return ops

# ----- System Info -----

@api_router.get("/system")
async def get_system_info():
    import random
    agents = await db.agents.find({}, {"_id": 0}).to_list(100)
    dispatch_count = await db.dispatches.count_documents({})
    note_count = await db.notes.count_documents({})
    forge_count = await db.forge.count_documents({})
    recent_ops = await db.operations.find({}, {"_id": 0}).sort("timestamp", -1).to_list(5)

    return {
        "gpu_devices": [
            {"name": "RTX 4070 Super #1", "load": random.randint(15, 85), "memory_used": random.randint(2, 8), "memory_total": 12},
            {"name": "RTX 4070 Super #2", "load": random.randint(0, 45), "memory_used": random.randint(0, 6), "memory_total": 12},
            {"name": "RTX 3050", "load": random.randint(0, 15), "memory_used": random.randint(0, 2), "memory_total": 8}
        ],
        "ram": {"used": round(random.uniform(5.0, 12.0), 1), "total": 32},
        "network": "online",
        "mempalace_size_mb": round(random.uniform(12.0, 80.0), 1),
        "agent_count": len(agents),
        "dispatch_count": dispatch_count,
        "note_count": note_count,
        "forge_count": forge_count,
        "recent_operations": recent_ops
    }

# ----- Models -----

@api_router.get("/models")
async def get_available_models():
    return [
        {"provider": "openai", "model": "gpt-5.2", "label": "GPT-5.2 (OpenAI)"},
        {"provider": "openai", "model": "gpt-5.1", "label": "GPT-5.1 (OpenAI)"},
        {"provider": "openai", "model": "gpt-4.1", "label": "GPT-4.1 (OpenAI)"},
        {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929", "label": "Claude Sonnet 4.5"},
        {"provider": "anthropic", "model": "claude-opus-4-5-20251101", "label": "Claude Opus 4.5"},
        {"provider": "gemini", "model": "gemini-3-flash-preview", "label": "Gemini 3 Flash"},
        {"provider": "gemini", "model": "gemini-2.5-pro", "label": "Gemini 2.5 Pro"},
    ]

# ----- Seed Default Agents -----

@app.on_event("startup")
async def seed_agents():
    existing = await db.agents.count_documents({})
    if existing == 0:
        defaults = [
            {
                "id": str(uuid.uuid4()),
                "name": "Hermes",
                "description": "Primary command agent. Excels at task planning, code generation, data analysis, and orchestrating multi-step workflows.",
                "operations": ["plan_task", "generate_code", "analyze_data", "summarize", "research"],
                "preferred_model": "gpt-5.2",
                "preferred_provider": "openai",
                "status": "idle",
                "created_at": now_iso(),
                "last_active": now_iso(),
                "dispatch_count": 0
            },
            {
                "id": str(uuid.uuid4()),
                "name": "OpenClaw",
                "description": "Creative operations agent. Specializes in design thinking, creative writing, branding, visual concepts, and artistic variations.",
                "operations": ["creative_writing", "design_concept", "branding", "visual_ideation", "copywriting"],
                "preferred_model": "gpt-5.2",
                "preferred_provider": "openai",
                "status": "idle",
                "created_at": now_iso(),
                "last_active": now_iso(),
                "dispatch_count": 0
            }
        ]
        for agent in defaults:
            await db.agents.insert_one(agent)
        await log_operation("SYSTEM_BOOT", "Nexus", "Default agents Hermes and OpenClaw initialized")
        logger.info("Seeded default agents: Hermes, OpenClaw")

# Include router + CORS
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
