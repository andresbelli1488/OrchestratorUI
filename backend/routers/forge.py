from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
import uuid
import base64
from shared import db, now_iso, log_operation, logger, EMERGENT_KEY, LlmChat, UserMessage, openai_image_gen, put_object, get_object, APP_NAME

router = APIRouter(prefix="/api")

class ForgeItemCreate(BaseModel):
    title: str
    type: str = "image"
    url: str = ""
    tags: List[str] = []
    source_agent: str = ""
    description: str = ""

class ImageGenRequest(BaseModel):
    prompt: str
    provider: str = "openai"
    title: str = ""
    tags: List[str] = []

@router.get("/forge")
async def get_forge_items(tag: Optional[str] = None):
    query = {"tags": tag} if tag else {}
    return await db.forge.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)

@router.post("/forge")
async def create_forge_item(item: ForgeItemCreate):
    doc = {
        "id": str(uuid.uuid4()), "title": item.title, "type": item.type, "url": item.url,
        "tags": item.tags, "source_agent": item.source_agent, "description": item.description,
        "storage_path": "", "created_at": now_iso()
    }
    await db.forge.insert_one(doc)
    await log_operation("FORGE_ITEM_ADDED", item.source_agent or "Manual", f"Added: {item.title}")
    doc.pop("_id", None)
    return doc

@router.delete("/forge/{item_id}")
async def delete_forge_item(item_id: str):
    result = await db.forge.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "deleted"}

@router.post("/forge/generate")
async def generate_image(req: ImageGenRequest):
    try:
        image_bytes = None
        gen_text = ""

        if req.provider == "gemini":
            chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"imggen-{uuid.uuid4()}", system_message="You are an image generation assistant.")
            chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
            msg = UserMessage(text=req.prompt)
            text, images = await chat.send_message_multimodal_response(msg)
            gen_text = text or ""
            if images and len(images) > 0:
                image_bytes = base64.b64decode(images[0]['data'])
        else:
            if not openai_image_gen:
                raise HTTPException(status_code=500, detail="Image generation not configured")
            result_images = await openai_image_gen.generate_images(prompt=req.prompt, model="gpt-image-1", number_of_images=1)
            if result_images and len(result_images) > 0:
                image_bytes = result_images[0]

        if not image_bytes:
            raise HTTPException(status_code=500, detail="No image generated")

        # Upload to object storage
        file_id = str(uuid.uuid4())
        storage_path = f"{APP_NAME}/forge/{file_id}.png"
        try:
            put_object(storage_path, image_bytes, "image/png")
            image_url = f"/api/files/{storage_path}"
        except Exception as storage_err:
            logger.warning(f"Storage upload failed, falling back to base64: {storage_err}")
            image_url = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            storage_path = ""

        title = req.title or f"Generated: {req.prompt[:50]}"
        forge_doc = {
            "id": str(uuid.uuid4()), "title": title, "type": "image", "url": image_url,
            "tags": list(set(req.tags + ["ai-generated", req.provider])),
            "source_agent": f"ImageGen ({req.provider})", "description": req.prompt,
            "storage_path": storage_path, "created_at": now_iso()
        }
        await db.forge.insert_one(forge_doc)
        forge_doc.pop("_id", None)
        await log_operation("IMAGE_GENERATED", f"ImageGen ({req.provider})", f"Prompt: {req.prompt[:60]}...", "SUCCESS")
        return {"image": image_url, "text": gen_text, "forge_item": forge_doc}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

@router.get("/files/{path:path}")
async def serve_file(path: str):
    """Proxy endpoint to serve files from object storage"""
    try:
        data, content_type = get_object(path)
        return Response(content=data, media_type=content_type)
    except Exception as e:
        logger.error(f"File serve error: {e}")
        raise HTTPException(status_code=404, detail="File not found")
