from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from shared import db, now_iso, log_operation
from routers.dispatches import DispatchCreate, create_dispatch

router = APIRouter(prefix="/api")

class OfflineQueueItem(BaseModel):
    agent_id: str
    prompt: str
    model_override: Optional[str] = None
    provider_override: Optional[str] = None

@router.post("/queue")
async def add_to_queue(item: OfflineQueueItem):
    agent = await db.agents.find_one({"id": item.agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    doc = {
        "id": str(uuid.uuid4()), "agent_id": item.agent_id, "agent_name": agent["name"],
        "prompt": item.prompt, "model_override": item.model_override,
        "provider_override": item.provider_override, "status": "queued", "created_at": now_iso()
    }
    await db.offline_queue.insert_one(doc)
    await log_operation("QUEUE_ADD", agent["name"], f"Queued: {item.prompt[:50]}...", "SUCCESS")
    doc.pop("_id", None)
    return doc

@router.get("/queue")
async def get_queue():
    return await db.offline_queue.find({}, {"_id": 0}).sort("created_at", 1).to_list(200)

@router.delete("/queue/{queue_id}")
async def remove_from_queue(queue_id: str):
    result = await db.offline_queue.delete_one({"id": queue_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return {"status": "deleted"}

@router.post("/queue/flush")
async def flush_queue():
    items = await db.offline_queue.find({}, {"_id": 0}).sort("created_at", 1).to_list(200)
    results = []
    for item in items:
        try:
            dispatch = DispatchCreate(agent_id=item["agent_id"], prompt=item["prompt"], model_override=item.get("model_override"), provider_override=item.get("provider_override"))
            result = await create_dispatch(dispatch)
            await db.offline_queue.delete_one({"id": item["id"]})
            results.append({"queue_id": item["id"], "dispatch_id": result["id"], "status": result["status"]})
        except Exception as e:
            results.append({"queue_id": item["id"], "status": "failed", "error": str(e)})
    await log_operation("QUEUE_FLUSH", "Nexus", f"Flushed {len(results)} queued dispatches", "SUCCESS")
    return {"flushed": len(results), "results": results}
