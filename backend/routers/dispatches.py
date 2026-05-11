from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import json
import asyncio
from shared import db, now_iso, log_operation, logger, EMERGENT_KEY, LlmChat, UserMessage

router = APIRouter(prefix="/api")

class DispatchCreate(BaseModel):
    agent_id: str
    prompt: str
    model_override: Optional[str] = None
    provider_override: Optional[str] = None

@router.post("/dispatches")
async def create_dispatch(dispatch: DispatchCreate):
    agent = await db.agents.find_one({"id": dispatch.agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    provider = dispatch.provider_override or agent.get("preferred_provider", "openai")
    model = dispatch.model_override or agent.get("preferred_model", "gpt-5.2")
    dispatch_doc = {
        "id": str(uuid.uuid4()), "agent_id": dispatch.agent_id, "agent_name": agent["name"],
        "prompt": dispatch.prompt, "model": model, "provider": provider,
        "status": "processing", "created_at": now_iso(), "response": None, "completed_at": None
    }
    await db.dispatches.insert_one(dispatch_doc)
    dispatch_doc.pop("_id", None)
    await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "busy", "last_active": now_iso()}, "$inc": {"dispatch_count": 1}})
    await log_operation("DISPATCH_SENT", agent["name"], f"Prompt: {dispatch.prompt[:80]}...", "PROCESSING")
    try:
        system_msg = f"You are {agent['name']}, an AI agent in the Hermes Command Nexus. {agent.get('description', '')}. You execute dispatched tasks with precision. Respond in a direct, technical manner befitting a command center operative."
        chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"dispatch-{dispatch_doc['id']}", system_message=system_msg)
        chat.with_model(provider, model)
        response_text = await chat.send_message(UserMessage(text=dispatch.prompt))
        dispatch_doc["response"] = response_text
        dispatch_doc["status"] = "completed"
        dispatch_doc["completed_at"] = now_iso()
        await db.dispatches.update_one({"id": dispatch_doc["id"]}, {"$set": {"response": response_text, "status": "completed", "completed_at": now_iso()}})
        await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "idle", "last_active": now_iso()}})
        await log_operation("TRANSMISSION_RECEIVED", agent["name"], f"Response received for dispatch {dispatch_doc['id']}", "SUCCESS")
    except Exception as e:
        logger.error(f"Dispatch execution error: {e}")
        dispatch_doc["response"] = f"[EXECUTION ERROR] {str(e)}"
        dispatch_doc["status"] = "failed"
        dispatch_doc["completed_at"] = now_iso()
        await db.dispatches.update_one({"id": dispatch_doc["id"]}, {"$set": {"response": dispatch_doc["response"], "status": "failed", "completed_at": now_iso()}})
        await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "error", "last_active": now_iso()}})
        await log_operation("DISPATCH_FAILED", agent["name"], str(e), "ERROR")
    return dispatch_doc

@router.get("/dispatches")
async def get_dispatches(agent_id: Optional[str] = None, limit: int = 50):
    query = {"agent_id": agent_id} if agent_id else {}
    return await db.dispatches.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)

@router.get("/dispatches/{dispatch_id}")
async def get_dispatch(dispatch_id: str):
    doc = await db.dispatches.find_one({"id": dispatch_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return doc

@router.post("/dispatches/stream")
async def stream_dispatch(dispatch: DispatchCreate):
    agent = await db.agents.find_one({"id": dispatch.agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    provider = dispatch.provider_override or agent.get("preferred_provider", "openai")
    model = dispatch.model_override or agent.get("preferred_model", "gpt-5.2")
    dispatch_id = str(uuid.uuid4())

    async def event_generator():
        dispatch_doc = {
            "id": dispatch_id, "agent_id": dispatch.agent_id, "agent_name": agent["name"],
            "prompt": dispatch.prompt, "model": model, "provider": provider,
            "status": "processing", "created_at": now_iso(), "response": None, "completed_at": None
        }
        await db.dispatches.insert_one(dispatch_doc)
        await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "busy", "last_active": now_iso()}, "$inc": {"dispatch_count": 1}})
        await log_operation("DISPATCH_SENT", agent["name"], f"Prompt: {dispatch.prompt[:80]}...", "PROCESSING")
        yield f"data: {json.dumps({'type': 'status', 'dispatch_id': dispatch_id, 'status': 'processing', 'agent': agent['name']})}\n\n"
        try:
            system_msg = f"You are {agent['name']}, an AI agent in the Hermes Command Nexus. {agent.get('description', '')}. You execute dispatched tasks with precision."
            chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"dispatch-{dispatch_id}", system_message=system_msg)
            chat.with_model(provider, model)
            response_text = await chat.send_message(UserMessage(text=dispatch.prompt))
            chunk_size = 12
            for i in range(0, len(response_text), chunk_size):
                yield f"data: {json.dumps({'type': 'chunk', 'content': response_text[i:i+chunk_size]})}\n\n"
                await asyncio.sleep(0.02)
            await db.dispatches.update_one({"id": dispatch_id}, {"$set": {"response": response_text, "status": "completed", "completed_at": now_iso()}})
            await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "idle", "last_active": now_iso()}})
            await log_operation("TRANSMISSION_RECEIVED", agent["name"], f"Streamed response for {dispatch_id}", "SUCCESS")
            yield f"data: {json.dumps({'type': 'complete', 'dispatch_id': dispatch_id, 'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(f"Stream dispatch error: {e}")
            err_msg = f"[EXECUTION ERROR] {str(e)}"
            await db.dispatches.update_one({"id": dispatch_id}, {"$set": {"response": err_msg, "status": "failed", "completed_at": now_iso()}})
            await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "error", "last_active": now_iso()}})
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
