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

### Phase 3 Features (2026-05-11)
- **Voice Selector Dropdown**: 8 ElevenLabs voices (George, Rachel, Antoni, Bella, Elli, Josh, Adam, Sam) with dropdown selector on TTS button
- **Image Generation for Forge**: Dual-provider support — OpenAI GPT Image 1 + Gemini Nano Banana, auto-adds generated images to Forge gallery with tags
- **Offline Mode Queue**: Toggle offline mode in header, dispatches queue locally, "Flush Queue" button executes all queued items when back online
- **Chain Drag-and-Drop Editor**: Steps have grip handles for drag reordering, flow preview (INPUT → Agent1 → Agent2 → OUTPUT), agent auto-selected
- **Remove RTX2**: GPU panel now shows only RTX 4070 Super #1 and RTX 3050
- All tests passing across 3 iterations (10/10 phase3 + all previous suites)

## Prioritized Backlog
### P0 (Next)
- Object storage for generated images (currently stored as base64 in MongoDB)
- Split server.py into routers (approaching 900 lines)

### P1
- Voice selection UI for TTS (8 voices available)
- Chain visual flow editor (drag & drop)
- Plugin marketplace / sharing
- Real GPU monitoring (when local)

### P2
- Cloud backup sync
- 3D avatar via react-three-fiber
- Atlas (3D printer fleet) integration
- Local model support (Ollama/Mistral)
- Export/import MemPalace data

## Next Tasks
1. Object storage for Forge images
2. Server.py router splitting
3. Chain template gallery
4. Plugin marketplace
