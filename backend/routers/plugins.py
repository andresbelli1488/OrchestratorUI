from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import json
import os
import subprocess
import tempfile
from shared import db, now_iso, log_operation, logger

router = APIRouter(prefix="/api")

class PluginCreate(BaseModel):
    name: str
    description: str = ""
    script: str
    input_schema: str = "text"
    output_schema: str = "text"
    is_builtin: bool = False

class PluginExecute(BaseModel):
    input_data: str = ""

@router.get("/plugins")
async def get_plugins():
    return await db.plugins.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)

@router.post("/plugins")
async def create_plugin(plugin: PluginCreate):
    doc = {
        "id": str(uuid.uuid4()), "name": plugin.name, "description": plugin.description,
        "script": plugin.script, "input_schema": plugin.input_schema,
        "output_schema": plugin.output_schema, "is_builtin": plugin.is_builtin,
        "created_at": now_iso(), "run_count": 0
    }
    await db.plugins.insert_one(doc)
    await log_operation("PLUGIN_REGISTERED", "Nexus", f"Plugin registered: {plugin.name}")
    doc.pop("_id", None)
    return doc

@router.delete("/plugins/{plugin_id}")
async def delete_plugin(plugin_id: str):
    plugin = await db.plugins.find_one({"id": plugin_id}, {"_id": 0})
    if plugin and plugin.get("is_builtin"):
        raise HTTPException(status_code=400, detail="Cannot delete built-in plugins")
    result = await db.plugins.delete_one({"id": plugin_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {"status": "deleted"}

@router.post("/plugins/{plugin_id}/execute")
async def execute_plugin(plugin_id: str, body: PluginExecute):
    plugin = await db.plugins.find_one({"id": plugin_id}, {"_id": 0})
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='/tmp') as f:
            safe_input = json.dumps(body.input_data)
            wrapper = f'import json as _json\nINPUT = _json.loads({safe_input!r})\n\n{plugin["script"]}'
            f.write(wrapper)
            f.flush()
            script_path = f.name
        result = subprocess.run(['python3', script_path], capture_output=True, text=True, timeout=30, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
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
