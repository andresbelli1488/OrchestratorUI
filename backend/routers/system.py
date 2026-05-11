from fastapi import APIRouter
import random
from shared import db

router = APIRouter(prefix="/api")

@router.get("/system")
async def get_system_info():
    agents = await db.agents.find({}, {"_id": 0}).to_list(100)
    dispatch_count = await db.dispatches.count_documents({})
    note_count = await db.notes.count_documents({})
    forge_count = await db.forge.count_documents({})
    recent_ops = await db.operations.find({}, {"_id": 0}).sort("timestamp", -1).to_list(5)
    return {
        "gpu_devices": [
            {"name": "RTX 4070 Super #1", "load": random.randint(15, 85), "memory_used": random.randint(2, 8), "memory_total": 12},
            {"name": "RTX 3050", "load": random.randint(0, 15), "memory_used": random.randint(0, 2), "memory_total": 8}
        ],
        "ram": {"used": round(random.uniform(5.0, 12.0), 1), "total": 32},
        "network": "online",
        "mempalace_size_mb": round(random.uniform(12.0, 80.0), 1),
        "agent_count": len(agents), "dispatch_count": dispatch_count,
        "note_count": note_count, "forge_count": forge_count, "recent_operations": recent_ops
    }

@router.get("/models")
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

@router.get("/operations")
async def get_operations(limit: int = 100):
    return await db.operations.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
