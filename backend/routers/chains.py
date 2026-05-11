from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import uuid
from shared import db, now_iso, log_operation, logger, EMERGENT_KEY, LlmChat, UserMessage

router = APIRouter(prefix="/api")

class ChainStepDef(BaseModel):
    agent_id: str
    prompt_template: str

class ChainCreate(BaseModel):
    name: str
    description: str = ""
    steps: List[ChainStepDef]

class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "general"
    steps: List[ChainStepDef]

@router.post("/chains")
async def create_chain(chain: ChainCreate):
    doc = {
        "id": str(uuid.uuid4()), "name": chain.name, "description": chain.description,
        "steps": [s.model_dump() for s in chain.steps], "created_at": now_iso(), "last_run": None, "run_count": 0
    }
    await db.chains.insert_one(doc)
    await log_operation("CHAIN_CREATED", "Nexus", f"Chain created: {chain.name}")
    doc.pop("_id", None)
    return doc

@router.get("/chains")
async def get_chains():
    return await db.chains.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)

@router.delete("/chains/{chain_id}")
async def delete_chain(chain_id: str):
    result = await db.chains.delete_one({"id": chain_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chain not found")
    return {"status": "deleted"}

@router.post("/chains/{chain_id}/execute")
async def execute_chain(chain_id: str, body: dict = None):
    chain = await db.chains.find_one({"id": chain_id}, {"_id": 0})
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    initial_input = (body or {}).get("input", "")
    results = []
    current_input = initial_input
    for i, step in enumerate(chain["steps"]):
        agent = await db.agents.find_one({"id": step["agent_id"]}, {"_id": 0})
        if not agent:
            results.append({"step": i, "error": f"Agent {step['agent_id']} not found"})
            break
        prompt = step["prompt_template"].replace("{input}", current_input)
        provider = agent.get("preferred_provider", "openai")
        model = agent.get("preferred_model", "gpt-5.2")
        try:
            chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"chain-{chain_id}-step-{i}", system_message=f"You are {agent['name']} in the Hermes Command Nexus. {agent.get('description', '')}. Execute the dispatched task precisely.")
            chat.with_model(provider, model)
            response_text = await chat.send_message(UserMessage(text=prompt))
            dispatch_doc = {
                "id": str(uuid.uuid4()), "agent_id": step["agent_id"], "agent_name": agent["name"],
                "prompt": prompt, "model": model, "provider": provider, "status": "completed",
                "created_at": now_iso(), "response": response_text, "completed_at": now_iso(),
                "chain_id": chain_id, "chain_step": i
            }
            await db.dispatches.insert_one(dispatch_doc)
            results.append({"step": i, "agent": agent["name"], "prompt": prompt, "response": response_text, "status": "completed"})
            current_input = response_text
        except Exception as e:
            results.append({"step": i, "agent": agent["name"], "error": str(e), "status": "failed"})
            break
    await db.chains.update_one({"id": chain_id}, {"$set": {"last_run": now_iso()}, "$inc": {"run_count": 1}})
    await log_operation("CHAIN_EXECUTED", "Nexus", f"Chain '{chain['name']}' executed ({len(results)} steps)", "SUCCESS" if all(r.get("status") == "completed" for r in results) else "ERROR")
    return {"chain_id": chain_id, "chain_name": chain["name"], "steps": results, "final_output": current_input}

# ----- Chain Templates -----

@router.get("/chain-templates")
async def get_templates():
    return await db.chain_templates.find({}, {"_id": 0}).sort("category", 1).to_list(100)

@router.post("/chain-templates")
async def create_template(tmpl: TemplateCreate):
    doc = {
        "id": str(uuid.uuid4()), "name": tmpl.name, "description": tmpl.description,
        "category": tmpl.category, "steps": [s.model_dump() for s in tmpl.steps],
        "created_at": now_iso(), "usage_count": 0
    }
    await db.chain_templates.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.post("/chain-templates/{template_id}/use")
async def use_template(template_id: str):
    tmpl = await db.chain_templates.find_one({"id": template_id}, {"_id": 0})
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    chain_doc = {
        "id": str(uuid.uuid4()), "name": f"{tmpl['name']} (copy)",
        "description": tmpl["description"], "steps": tmpl["steps"],
        "created_at": now_iso(), "last_run": None, "run_count": 0
    }
    await db.chains.insert_one(chain_doc)
    await db.chain_templates.update_one({"id": template_id}, {"$inc": {"usage_count": 1}})
    await log_operation("TEMPLATE_USED", "Nexus", f"Template '{tmpl['name']}' cloned as chain")
    chain_doc.pop("_id", None)
    return chain_doc

@router.delete("/chain-templates/{template_id}")
async def delete_template(template_id: str):
    result = await db.chain_templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"status": "deleted"}
