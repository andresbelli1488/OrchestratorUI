from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
from shared import db, now_iso, log_operation

router = APIRouter(prefix="/api")

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

@router.get("/agents")
async def get_agents():
    return await db.agents.find({}, {"_id": 0}).to_list(100)

@router.post("/agents")
async def create_agent(agent: AgentCreate):
    doc = {
        "id": str(uuid.uuid4()), "name": agent.name, "description": agent.description,
        "operations": agent.operations, "preferred_model": agent.preferred_model,
        "preferred_provider": agent.preferred_provider, "status": "idle",
        "created_at": now_iso(), "last_active": now_iso(), "dispatch_count": 0
    }
    await db.agents.insert_one(doc)
    await log_operation("AGENT_REGISTERED", agent.name, f"Agent {agent.name} registered")
    doc.pop("_id", None)
    return doc

@router.patch("/agents/{agent_id}")
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
