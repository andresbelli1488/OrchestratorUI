"""Hermes Command Nexus — Main application entry point."""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import os
import uuid

from shared import db, logger, now_iso, log_operation, init_storage

# Import routers
from routers.agents import router as agents_router
from routers.dispatches import router as dispatches_router
from routers.voice import router as voice_router
from routers.forge import router as forge_router
from routers.chains import router as chains_router
from routers.plugins import router as plugins_router
from routers.mempalace import router as mempalace_router
from routers.system import router as system_router
from routers.queue import router as queue_router

app = FastAPI(title="Hermes Command Nexus")

# Include all routers
for r in [agents_router, dispatches_router, voice_router, forge_router, chains_router, plugins_router, mempalace_router, system_router, queue_router]:
    app.include_router(r)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Init object storage
    try:
        init_storage()
    except Exception as e:
        logger.warning(f"Object storage init failed (will retry on first use): {e}")

    # Seed default agents
    if await db.agents.count_documents({}) == 0:
        for agent_data in [
            {"name": "Hermes", "description": "Primary command agent. Excels at task planning, code generation, data analysis, and orchestrating multi-step workflows.", "operations": ["plan_task", "generate_code", "analyze_data", "summarize", "research"], "preferred_model": "gpt-5.2", "preferred_provider": "openai"},
            {"name": "OpenClaw", "description": "Creative operations agent. Specializes in design thinking, creative writing, branding, visual concepts, and artistic variations.", "operations": ["creative_writing", "design_concept", "branding", "visual_ideation", "copywriting"], "preferred_model": "gpt-5.2", "preferred_provider": "openai"},
        ]:
            doc = {**agent_data, "id": str(uuid.uuid4()), "status": "idle", "created_at": now_iso(), "last_active": now_iso(), "dispatch_count": 0}
            await db.agents.insert_one(doc)
        await log_operation("SYSTEM_BOOT", "Nexus", "Default agents Hermes and OpenClaw initialized")
        logger.info("Seeded default agents")

    # Seed default plugins
    if await db.plugins.count_documents({}) == 0:
        for p in [
            {"name": "Word Counter", "description": "Count words, characters, and lines in text input.", "script": "text = INPUT\nwords = len(text.split())\nchars = len(text)\nlines = len(text.splitlines())\nprint(f'Words: {words}')\nprint(f'Characters: {chars}')\nprint(f'Lines: {lines}')"},
            {"name": "JSON Formatter", "description": "Pretty-print and validate JSON data.", "script": "import json\ntry:\n    data = json.loads(INPUT)\n    print(json.dumps(data, indent=2))\nexcept json.JSONDecodeError as e:\n    print(f'Invalid JSON: {e}')"},
            {"name": "CSV to Table", "description": "Convert CSV data to a formatted table.", "script": "import csv\nimport io\nreader = csv.reader(io.StringIO(INPUT))\nrows = list(reader)\nif not rows:\n    print('Empty CSV')\nelse:\n    widths = [max(len(str(row[i])) if i < len(row) else 0 for row in rows) for i in range(max(len(r) for r in rows))]\n    for row in rows:\n        print(' | '.join(str(row[i]).ljust(widths[i]) if i < len(row) else ' '*widths[i] for i in range(len(widths))))"},
            {"name": "Base64 Encode/Decode", "description": "Encode text to Base64 or decode Base64 to text.", "script": "import base64\ntext = INPUT.strip()\ntry:\n    decoded = base64.b64decode(text).decode('utf-8')\n    print(f'Decoded: {decoded}')\nexcept Exception:\n    encoded = base64.b64encode(text.encode()).decode()\n    print(f'Encoded: {encoded}')"},
            {"name": "Text Statistics", "description": "Analyze text: frequency analysis, unique words, avg word length.", "script": "from collections import Counter\ntext = INPUT\nwords = text.lower().split()\ncounter = Counter(words)\nprint(f'Total words: {len(words)}')\nprint(f'Unique words: {len(counter)}')\nif words:\n    avg_len = sum(len(w) for w in words) / len(words)\n    print(f'Avg word length: {avg_len:.1f}')\n    print(f'\\nTop 10 words:')\n    for word, count in counter.most_common(10):\n        print(f'  {word}: {count}')"},
        ]:
            doc = {**p, "id": str(uuid.uuid4()), "input_schema": "text", "output_schema": "text", "is_builtin": True, "created_at": now_iso(), "run_count": 0}
            await db.plugins.insert_one(doc)
        logger.info("Seeded 5 built-in plugins")

    # Seed chain templates
    if await db.chain_templates.count_documents({}) == 0:
        agents = await db.agents.find({}, {"_id": 0}).to_list(10)
        agent_map = {a["name"]: a["id"] for a in agents}
        hermes_id = agent_map.get("Hermes", "")
        openclaw_id = agent_map.get("OpenClaw", "")
        if hermes_id and openclaw_id:
            templates = [
                {"name": "Research & Summarize", "description": "Hermes researches a topic, then summarizes findings concisely.", "category": "research", "steps": [{"agent_id": hermes_id, "prompt_template": "Research the following topic in depth: {input}"}, {"agent_id": hermes_id, "prompt_template": "Summarize the following research into 3 key bullet points: {input}"}]},
                {"name": "Creative Brief Pipeline", "description": "Hermes outlines the problem, OpenClaw generates creative variations.", "category": "creative", "steps": [{"agent_id": hermes_id, "prompt_template": "Analyze this creative brief and outline the key objectives, target audience, and constraints: {input}"}, {"agent_id": openclaw_id, "prompt_template": "Based on this analysis, generate 3 creative concept variations with different visual directions: {input}"}]},
                {"name": "Code Review Chain", "description": "Hermes reviews code for bugs, then generates improved version.", "category": "development", "steps": [{"agent_id": hermes_id, "prompt_template": "Review this code for bugs, performance issues, and best practices: {input}"}, {"agent_id": hermes_id, "prompt_template": "Based on this code review, generate the improved version of the code with all fixes applied: {input}"}]},
                {"name": "Brand Voice Generator", "description": "Hermes analyzes brand context, OpenClaw creates content in that voice.", "category": "creative", "steps": [{"agent_id": hermes_id, "prompt_template": "Analyze this brand and define its voice, tone, values, and communication style: {input}"}, {"agent_id": openclaw_id, "prompt_template": "Using this brand voice guide, write 5 social media posts that match the brand perfectly: {input}"}]},
                {"name": "Data → Insight → Action", "description": "Hermes analyzes data, then recommends actions.", "category": "analysis", "steps": [{"agent_id": hermes_id, "prompt_template": "Analyze this data and extract the key insights and patterns: {input}"}, {"agent_id": hermes_id, "prompt_template": "Based on these insights, recommend 3 specific actionable steps with expected outcomes: {input}"}]},
            ]
            for tmpl in templates:
                doc = {**tmpl, "id": str(uuid.uuid4()), "created_at": now_iso(), "usage_count": 0}
                await db.chain_templates.insert_one(doc)
            logger.info("Seeded 5 chain templates")

@app.on_event("shutdown")
async def shutdown():
    from shared import client
    client.close()
