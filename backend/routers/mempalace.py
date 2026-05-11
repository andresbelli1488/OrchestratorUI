from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import re
import uuid
from shared import db, now_iso, log_operation

router = APIRouter(prefix="/api")

class NoteCreate(BaseModel):
    content: str
    tags: List[str] = []

class NoteUpdate(BaseModel):
    content: Optional[str] = None
    tags: Optional[List[str]] = None

@router.get("/mempalace/notes")
async def get_notes(search: Optional[str] = None):
    query = {}
    if search:
        query["$or"] = [{"content": {"$regex": search, "$options": "i"}}, {"tags": {"$regex": search, "$options": "i"}}]
    return await db.notes.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)

@router.post("/mempalace/notes")
async def create_note(note: NoteCreate):
    doc = {"id": str(uuid.uuid4()), "content": note.content, "tags": note.tags, "created_at": now_iso(), "updated_at": now_iso()}
    await db.notes.insert_one(doc)
    await log_operation("NOTE_CREATED", "MemPalace", f"Note created: {note.content[:50]}...")
    doc.pop("_id", None)
    return doc

@router.patch("/mempalace/notes/{note_id}")
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

@router.delete("/mempalace/notes/{note_id}")
async def delete_note(note_id: str):
    result = await db.notes.delete_one({"id": note_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "deleted"}

@router.get("/mempalace/search")
async def search_mempalace(q: str):
    escaped = re.escape(q)
    regex = {"$regex": escaped, "$options": "i"}
    notes = await db.notes.find({"$or": [{"content": regex}, {"tags": regex}]}, {"_id": 0}).to_list(100)
    dispatches = await db.dispatches.find({"$or": [{"prompt": regex}, {"response": regex}]}, {"_id": 0}).to_list(100)
    return {"notes": notes, "transmissions": dispatches}
