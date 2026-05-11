from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import io
import json
import base64
import asyncio
import subprocess
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from emergentintegrations.llm.openai import OpenAISpeechToText
from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
from elevenlabs import ElevenLabs as ElevenLabsClient
from elevenlabs import VoiceSettings

import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
ELEVENLABS_KEY = os.environ.get('ELEVENLABS_API_KEY', '')

# ElevenLabs client
eleven_client = ElevenLabsClient(api_key=ELEVENLABS_KEY) if ELEVENLABS_KEY else None

# Whisper STT client
stt_client = OpenAISpeechToText(api_key=EMERGENT_KEY) if EMERGENT_KEY else None

# Image generation clients
openai_image_gen = OpenAIImageGeneration(api_key=EMERGENT_KEY) if EMERGENT_KEY else None

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

class ChainStepDef(BaseModel):
    agent_id: str
    prompt_template: str  # Use {input} as placeholder for previous step output

class ChainCreate(BaseModel):
    name: str
    description: str = ""
    steps: List[ChainStepDef]

class PluginCreate(BaseModel):
    name: str
    description: str = ""
    script: str
    input_schema: str = "text"
    output_schema: str = "text"
    is_builtin: bool = False

class PluginExecute(BaseModel):
    input_data: str = ""

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb"

class ImageGenRequest(BaseModel):
    prompt: str
    provider: str = "openai"  # "openai" or "gemini"
    title: str = ""
    tags: List[str] = []

class OfflineQueueItem(BaseModel):
    agent_id: str
    prompt: str
    model_override: Optional[str] = None
    provider_override: Optional[str] = None

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

# ----- Streaming Dispatch -----

@api_router.post("/dispatches/stream")
async def stream_dispatch(dispatch: DispatchCreate):
    agent = await db.agents.find_one({"id": dispatch.agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    provider = dispatch.provider_override or agent.get("preferred_provider", "openai")
    model = dispatch.model_override or agent.get("preferred_model", "gpt-5.2")

    dispatch_id = str(uuid.uuid4())

    async def event_generator():
        dispatch_doc = {
            "id": dispatch_id,
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
        await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "busy", "last_active": now_iso()}, "$inc": {"dispatch_count": 1}})
        await log_operation("DISPATCH_SENT", agent["name"], f"Prompt: {dispatch.prompt[:80]}...", "PROCESSING")

        yield f"data: {json.dumps({'type': 'status', 'dispatch_id': dispatch_id, 'status': 'processing', 'agent': agent['name']})}\n\n"

        try:
            system_msg = f"You are {agent['name']}, an AI agent in the Hermes Command Nexus. {agent.get('description', '')}. You execute dispatched tasks with precision. Respond in a direct, technical manner befitting a command center operative."
            chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"dispatch-{dispatch_id}", system_message=system_msg)
            chat.with_model(provider, model)
            user_message = UserMessage(text=dispatch.prompt)
            response_text = await chat.send_message(user_message)

            # Stream response in chunks for real-time feel
            chunk_size = 12
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0.02)

            # Save completed dispatch
            await db.dispatches.update_one(
                {"id": dispatch_id},
                {"$set": {"response": response_text, "status": "completed", "completed_at": now_iso()}}
            )
            await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "idle", "last_active": now_iso()}})
            await log_operation("TRANSMISSION_RECEIVED", agent["name"], f"Streamed response for {dispatch_id}", "SUCCESS")

            yield f"data: {json.dumps({'type': 'complete', 'dispatch_id': dispatch_id, 'status': 'completed'})}\n\n"

        except Exception as e:
            logger.error(f"Stream dispatch error: {e}")
            err_msg = f"[EXECUTION ERROR] {str(e)}"
            await db.dispatches.update_one(
                {"id": dispatch_id},
                {"$set": {"response": err_msg, "status": "failed", "completed_at": now_iso()}}
            )
            await db.agents.update_one({"id": dispatch.agent_id}, {"$set": {"status": "error", "last_active": now_iso()}})
            await log_operation("DISPATCH_FAILED", agent["name"], str(e), "ERROR")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ----- Voice Endpoints -----

@api_router.post("/voice/transcribe")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """Transcribe audio to text using Whisper"""
    if not stt_client:
        raise HTTPException(status_code=500, detail="STT not configured")
    try:
        audio_content = await audio_file.read()
        audio_io = io.BytesIO(audio_content)
        audio_io.name = audio_file.filename or "audio.webm"
        response = await stt_client.transcribe(file=audio_io, model="whisper-1", response_format="json")
        text = response.text if hasattr(response, 'text') else str(response)
        await log_operation("VOICE_TRANSCRIBE", "Whisper", f"Transcribed: {text[:50]}...", "SUCCESS")
        return {"text": text}
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@api_router.post("/voice/speak")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech using ElevenLabs"""
    if not eleven_client:
        raise HTTPException(status_code=500, detail="TTS not configured")
    try:
        audio_generator = eleven_client.text_to_speech.convert(
            text=request.text[:5000],
            voice_id=request.voice_id,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.0, use_speaker_boost=True)
        )
        audio_data = b""
        for chunk in audio_generator:
            audio_data += chunk
        audio_b64 = base64.b64encode(audio_data).decode()
        await log_operation("VOICE_SPEAK", "ElevenLabs", f"Generated speech: {request.text[:50]}...", "SUCCESS")
        return {"audio": f"data:audio/mpeg;base64,{audio_b64}"}
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

@api_router.get("/voice/voices")
async def get_voices():
    """Get available ElevenLabs voices"""
    # Return popular default voices (key may not have voices_read permission)
    default_voices = [
        {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "name": "George", "category": "premade"},
        {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "category": "premade"},
        {"voice_id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "category": "premade"},
        {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "category": "premade"},
        {"voice_id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "category": "premade"},
        {"voice_id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "category": "premade"},
        {"voice_id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "category": "premade"},
        {"voice_id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam", "category": "premade"},
    ]
    if not eleven_client:
        return default_voices
    try:
        voices_response = eleven_client.voices.get_all()
        return [{"voice_id": v.voice_id, "name": v.name, "category": getattr(v, 'category', 'unknown')} for v in voices_response.voices[:20]]
    except Exception as e:
        logger.warning(f"Get voices fallback to defaults: {e}")
        return default_voices

# ----- Image Generation -----

@api_router.post("/forge/generate")
async def generate_image(req: ImageGenRequest):
    """Generate an image using OpenAI GPT Image 1 or Gemini Nano Banana"""
    try:
        image_b64 = None
        gen_text = ""

        if req.provider == "gemini":
            chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"imggen-{uuid.uuid4()}", system_message="You are an image generation assistant.")
            chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
            msg = UserMessage(text=req.prompt)
            text, images = await chat.send_message_multimodal_response(msg)
            gen_text = text or ""
            if images and len(images) > 0:
                image_b64 = images[0]['data']
        else:
            # OpenAI GPT Image 1
            if not openai_image_gen:
                raise HTTPException(status_code=500, detail="Image generation not configured")
            images = await openai_image_gen.generate_images(prompt=req.prompt, model="gpt-image-1", number_of_images=1)
            if images and len(images) > 0:
                image_b64 = base64.b64encode(images[0]).decode('utf-8')

        if not image_b64:
            raise HTTPException(status_code=500, detail="No image generated")

        # Auto-add to Forge
        title = req.title or f"Generated: {req.prompt[:50]}"
        data_url = f"data:image/png;base64,{image_b64}"
        forge_doc = {
            "id": str(uuid.uuid4()),
            "title": title,
            "type": "image",
            "url": data_url,
            "tags": req.tags + ["ai-generated", req.provider],
            "source_agent": f"ImageGen ({req.provider})",
            "description": req.prompt,
            "created_at": now_iso()
        }
        await db.forge.insert_one(forge_doc)
        forge_doc.pop("_id", None)
        await log_operation("IMAGE_GENERATED", f"ImageGen ({req.provider})", f"Prompt: {req.prompt[:60]}...", "SUCCESS")

        return {"image": data_url, "text": gen_text, "forge_item": forge_doc}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

# ----- Offline Queue -----

@api_router.post("/queue")
async def add_to_queue(item: OfflineQueueItem):
    """Add a dispatch to the offline queue"""
    agent = await db.agents.find_one({"id": item.agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    doc = {
        "id": str(uuid.uuid4()),
        "agent_id": item.agent_id,
        "agent_name": agent["name"],
        "prompt": item.prompt,
        "model_override": item.model_override,
        "provider_override": item.provider_override,
        "status": "queued",
        "created_at": now_iso()
    }
    await db.offline_queue.insert_one(doc)
    await log_operation("QUEUE_ADD", agent["name"], f"Queued: {item.prompt[:50]}...", "SUCCESS")
    doc.pop("_id", None)
    return doc

@api_router.get("/queue")
async def get_queue():
    """Get all queued dispatches"""
    items = await db.offline_queue.find({}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return items

@api_router.delete("/queue/{queue_id}")
async def remove_from_queue(queue_id: str):
    result = await db.offline_queue.delete_one({"id": queue_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return {"status": "deleted"}

@api_router.post("/queue/flush")
async def flush_queue():
    """Execute all queued dispatches"""
    items = await db.offline_queue.find({}, {"_id": 0}).sort("created_at", 1).to_list(200)
    results = []
    for item in items:
        try:
            dispatch = DispatchCreate(
                agent_id=item["agent_id"],
                prompt=item["prompt"],
                model_override=item.get("model_override"),
                provider_override=item.get("provider_override")
            )
            result = await create_dispatch(dispatch)
            await db.offline_queue.delete_one({"id": item["id"]})
            results.append({"queue_id": item["id"], "dispatch_id": result["id"], "status": result["status"]})
        except Exception as e:
            results.append({"queue_id": item["id"], "status": "failed", "error": str(e)})
    await log_operation("QUEUE_FLUSH", "Nexus", f"Flushed {len(results)} queued dispatches", "SUCCESS")
    return {"flushed": len(results), "results": results}

# ----- Dispatch Chains -----

@api_router.post("/chains")
async def create_chain(chain: ChainCreate):
    doc = {
        "id": str(uuid.uuid4()),
        "name": chain.name,
        "description": chain.description,
        "steps": [s.model_dump() for s in chain.steps],
        "created_at": now_iso(),
        "last_run": None,
        "run_count": 0
    }
    await db.chains.insert_one(doc)
    await log_operation("CHAIN_CREATED", "Nexus", f"Chain created: {chain.name}")
    doc.pop("_id", None)
    return doc

@api_router.get("/chains")
async def get_chains():
    chains = await db.chains.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return chains

@api_router.delete("/chains/{chain_id}")
async def delete_chain(chain_id: str):
    result = await db.chains.delete_one({"id": chain_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chain not found")
    return {"status": "deleted"}

@api_router.post("/chains/{chain_id}/execute")
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
            system_msg = f"You are {agent['name']} in the Hermes Command Nexus. {agent.get('description', '')}. Execute the dispatched task precisely."
            chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"chain-{chain_id}-step-{i}", system_message=system_msg)
            chat.with_model(provider, model)
            response_text = await chat.send_message(UserMessage(text=prompt))

            # Store dispatch record
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

# ----- Plugin System -----

@api_router.post("/plugins")
async def create_plugin(plugin: PluginCreate):
    doc = {
        "id": str(uuid.uuid4()),
        "name": plugin.name,
        "description": plugin.description,
        "script": plugin.script,
        "input_schema": plugin.input_schema,
        "output_schema": plugin.output_schema,
        "is_builtin": plugin.is_builtin,
        "created_at": now_iso(),
        "run_count": 0
    }
    await db.plugins.insert_one(doc)
    await log_operation("PLUGIN_REGISTERED", "Nexus", f"Plugin registered: {plugin.name}")
    doc.pop("_id", None)
    return doc

@api_router.get("/plugins")
async def get_plugins():
    plugins = await db.plugins.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return plugins

@api_router.delete("/plugins/{plugin_id}")
async def delete_plugin(plugin_id: str):
    plugin = await db.plugins.find_one({"id": plugin_id}, {"_id": 0})
    if plugin and plugin.get("is_builtin"):
        raise HTTPException(status_code=400, detail="Cannot delete built-in plugins")
    result = await db.plugins.delete_one({"id": plugin_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {"status": "deleted"}

@api_router.post("/plugins/{plugin_id}/execute")
async def execute_plugin(plugin_id: str, body: PluginExecute):
    plugin = await db.plugins.find_one({"id": plugin_id}, {"_id": 0})
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='/tmp') as f:
            # Inject input as variable safely
            safe_input = json.dumps(body.input_data)
            wrapper = f'import json as _json\nINPUT = _json.loads({safe_input!r})\n\n{plugin["script"]}'
            f.write(wrapper)
            f.flush()
            script_path = f.name

        result = subprocess.run(
            ['python3', script_path],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        )
        os.unlink(script_path)

        output = result.stdout or ""
        error = result.stderr or ""
        status = "success" if result.returncode == 0 else "error"

        await db.plugins.update_one({"id": plugin_id}, {"$inc": {"run_count": 1}})
        await log_operation("PLUGIN_EXECUTED", plugin["name"], f"Exit code: {result.returncode}", "SUCCESS" if status == "success" else "ERROR")

        return {"output": output, "error": error, "status": status, "exit_code": result.returncode}

    except subprocess.TimeoutExpired:
        await log_operation("PLUGIN_TIMEOUT", plugin["name"], "Execution timed out after 30s", "ERROR")
        return {"output": "", "error": "Execution timed out (30s limit)", "status": "timeout", "exit_code": -1}
    except Exception as e:
        return {"output": "", "error": str(e), "status": "error", "exit_code": -1}

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

    # Seed default plugins
    existing_plugins = await db.plugins.count_documents({})
    if existing_plugins == 0:
        builtin_plugins = [
            {
                "id": str(uuid.uuid4()), "name": "Word Counter",
                "description": "Count words, characters, and lines in text input.",
                "script": "text = INPUT\nwords = len(text.split())\nchars = len(text)\nlines = len(text.splitlines())\nprint(f'Words: {words}')\nprint(f'Characters: {chars}')\nprint(f'Lines: {lines}')",
                "input_schema": "text", "output_schema": "text", "is_builtin": True, "created_at": now_iso(), "run_count": 0
            },
            {
                "id": str(uuid.uuid4()), "name": "JSON Formatter",
                "description": "Pretty-print and validate JSON data.",
                "script": "import json\ntry:\n    data = json.loads(INPUT)\n    print(json.dumps(data, indent=2))\nexcept json.JSONDecodeError as e:\n    print(f'Invalid JSON: {e}')",
                "input_schema": "text", "output_schema": "text", "is_builtin": True, "created_at": now_iso(), "run_count": 0
            },
            {
                "id": str(uuid.uuid4()), "name": "CSV to Table",
                "description": "Convert CSV data to a formatted table.",
                "script": "import csv\nimport io\nreader = csv.reader(io.StringIO(INPUT))\nrows = list(reader)\nif not rows:\n    print('Empty CSV')\nelse:\n    widths = [max(len(str(row[i])) if i < len(row) else 0 for row in rows) for i in range(max(len(r) for r in rows))]\n    for row in rows:\n        print(' | '.join(str(row[i]).ljust(widths[i]) if i < len(row) else ' '*widths[i] for i in range(len(widths))))",
                "input_schema": "text", "output_schema": "text", "is_builtin": True, "created_at": now_iso(), "run_count": 0
            },
            {
                "id": str(uuid.uuid4()), "name": "Base64 Encode/Decode",
                "description": "Encode text to Base64 or decode Base64 to text.",
                "script": "import base64\ntext = INPUT.strip()\ntry:\n    decoded = base64.b64decode(text).decode('utf-8')\n    print(f'Decoded: {decoded}')\nexcept Exception:\n    encoded = base64.b64encode(text.encode()).decode()\n    print(f'Encoded: {encoded}')",
                "input_schema": "text", "output_schema": "text", "is_builtin": True, "created_at": now_iso(), "run_count": 0
            },
            {
                "id": str(uuid.uuid4()), "name": "Text Statistics",
                "description": "Analyze text: frequency analysis, unique words, avg word length.",
                "script": "from collections import Counter\ntext = INPUT\nwords = text.lower().split()\ncounter = Counter(words)\nprint(f'Total words: {len(words)}')\nprint(f'Unique words: {len(counter)}')\nif words:\n    avg_len = sum(len(w) for w in words) / len(words)\n    print(f'Avg word length: {avg_len:.1f}')\n    print(f'\\nTop 10 words:')\n    for word, count in counter.most_common(10):\n        print(f'  {word}: {count}')",
                "input_schema": "text", "output_schema": "text", "is_builtin": True, "created_at": now_iso(), "run_count": 0
            },
        ]
        for plugin in builtin_plugins:
            await db.plugins.insert_one(plugin)
        logger.info("Seeded 5 built-in plugins")

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
