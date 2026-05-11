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
- All 8 navigation tabs: Command, MemPalace, Forge, Chains, Plugins, Services, Ops Log, Models
- Animated agent avatars with state-reactive visuals
- Terminal-style dispatch console with `agent@nexus:~$` prompt
- GPU/RAM/network monitoring panel (simulated)
- MemPalace with CRUD, search, tagging
- Forge gallery with type-based icons and image previews
- Service registry with agent registration form
- Operations log with auto-refresh and color-coded severity
- Model switcher with per-agent model assignment

### Phase 2 Features (2026-05-11)
- **Streaming SSE Dispatch**: Real-time token-by-token response streaming via Server-Sent Events
- **Voice-to-Voice**: Whisper STT for voice input (mic button), ElevenLabs TTS for voice output (speaker button)
- **Dispatch Chains**: Multi-agent workflow builder (create chains, wire Hermes→OpenClaw→Forge, execute with input)
- **Plugin System**: Server-side Python execution, 5 built-in plugins (Word Counter, JSON Formatter, CSV to Table, Base64, Text Statistics), custom plugin creation
- 100% backend + frontend tests passing across 2 iterations

## Prioritized Backlog
### P0 (Next)
- Actual GPU monitoring (when running locally)
- Image generation in Forge via DALL-E/Stable Diffusion

### P1
- Offline mode with queued dispatches
- Voice selection UI for TTS (8 voices available)
- Chain visual flow editor (drag & drop)
- Plugin marketplace / sharing

### P2
- Cloud backup sync
- 3D avatar via react-three-fiber
- Atlas (3D printer fleet) integration
- Local model support (Ollama/Mistral)
- Export/import MemPalace data

## Next Tasks
1. Image generation integration for Forge
2. Voice selector dropdown for TTS
3. Chain visual drag-and-drop editor
4. Offline mode queue
