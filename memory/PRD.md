# Hermes Command Nexus - PRD

## Original Problem Statement
A sovereign local operating system / unified command center for AI agents. Hermes Command Nexus orchestrates local AI agents (Hermes, OpenClaw, etc.) with MemPalace as the brain, service registry, Forge output gallery, operations log, and model switcher. Dark hacker terminal aesthetic.

## Architecture
- **Backend**: FastAPI + MongoDB + OpenAI GPT-5.2 (via emergentintegrations)
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Database**: MongoDB (collections: agents, dispatches, notes, forge, operations)
- **AI**: GPT-5.2 via Emergent LLM Key

## User Persona
- Power user / developer managing local AI agents
- Single-user, no authentication needed

## Core Requirements (Static)
1. Agent dashboard with real-time status
2. Dispatch console to send tasks to AI agents
3. MemPalace: notes, transmission history, search
4. Forge: output gallery with tagging
5. Service registry for agent management
6. System info panel (GPU/RAM/network)
7. Operations log (audit trail)
8. Model switcher per agent

## What's Been Implemented (2026-05-11)
- Full backend with all CRUD endpoints (agents, dispatches, notes, forge, operations, system, models)
- AI dispatch via GPT-5.2 with real responses
- Default agents (Hermes, OpenClaw) seeded on startup
- Dark hacker terminal UI with JetBrains Mono + IBM Plex Sans fonts
- All 6 navigation tabs: Command, MemPalace, Forge, Services, Ops Log, Models
- Animated agent avatars with state-reactive visuals
- Terminal-style dispatch console with `agent@nexus:~$` prompt
- GPU/RAM/network monitoring panel (simulated)
- MemPalace with CRUD, search, tagging
- Forge gallery with type-based icons and image previews
- Service registry with agent registration form
- Operations log with auto-refresh and color-coded severity
- Model switcher with per-agent model assignment
- 100% backend tests passing (15/15), 100% frontend flows verified

## Prioritized Backlog
### P0 (Next)
- Dispatch chain support ("Ask Hermes → pass to OpenClaw → dump to Forge")
- Streaming responses for long dispatches

### P1
- Voice-to-text for MemPalace notes (Whisper integration)
- Actual GPU monitoring (when running locally)
- Plugin system for custom Python scripts as services
- Image generation in Forge via DALL-E/Stable Diffusion

### P2
- Offline mode with queued dispatches
- Cloud backup sync
- 3D avatar via react-three-fiber
- Atlas (3D printer fleet) integration
- Local model support (Ollama/Mistral)
- Export/import MemPalace data

## Next Tasks
1. Implement dispatch chains (multi-agent workflows)
2. Add streaming responses
3. Voice-to-text integration for notes
4. Plugin system for custom tools
