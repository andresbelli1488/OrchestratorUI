"# Hermes Command Nexus

A sovereign command center for orchestrating AI agents — dispatch tasks, chain multi-agent workflows, generate images, manage plugins, and maintain full operational history. All intelligence stays on your hardware.

![Stack](https://img.shields.io/badge/React_19-black?style=flat&logo=react) ![FastAPI](https://img.shields.io/badge/FastAPI-black?style=flat&logo=fastapi) ![MongoDB](https://img.shields.io/badge/MongoDB-black?style=flat&logo=mongodb) ![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-black?style=flat&logo=tailwindcss)

---

## Overview

Hermes Command Nexus is a unified interface for managing local AI agents. It uses **Womb language** — you \"dispatch\" tasks to agents, watch \"transmissions\" (responses stream in real-time via SSE), view \"Forge output\" (AI-generated images, code, designs), and maintain an \"operations log\" (full audit trail).

### Core Agents

| Agent | Role |
|---|---|
| **Hermes** | Primary command agent — task planning, code generation, data analysis, research |
| **OpenClaw** | Creative operations — design thinking, branding, visual concepts, copywriting |

Additional agents can be registered dynamically through the Service Registry.

---

## Features

### Command Center
- Real-time agent status monitoring (idle / busy / error)
- Animated state-reactive agent avatars
- GPU / RAM / network telemetry panel
- Operations log with live auto-refresh

### Dispatch Console
- Terminal-style input with `agent@nexus:~$` prompt
- **SSE Streaming** — responses render token-by-token in real-time
- **Voice Input** — Whisper STT records from mic, transcribes to text
- **Voice Output** — ElevenLabs TTS with 8 selectable voices (George, Rachel, Antoni, Bella, Elli, Josh, Adam, Sam)
- **Offline Mode** — queue dispatches locally, flush when back online

### Forge Gallery
- Unified output gallery for all AI-generated content
- **Async Image Generation** — dual-provider support:
  - OpenAI GPT Image 1
  - Gemini Nano Banana (gemini-3.1-flash-image-preview)
- Images stored in Emergent Object Storage with proxy serving
- Tagged, searchable, exportable

### Dispatch Chains
- Multi-agent workflow builder with **drag-and-drop reordering**
- Visual flow preview: `INPUT -> Hermes -> OpenClaw -> OUTPUT`
- `{input}` placeholder passes output between steps
- **Template Gallery** — 5 pre-built chain templates:
  - Research & Summarize
  - Creative Brief Pipeline
  - Code Review Chain
  - Brand Voice Generator
  - Data -> Insight -> Action

### Plugin System
- Server-side Python script execution (30s timeout)
- 5 built-in plugins: Word Counter, JSON Formatter, CSV to Table, Base64 Encode/Decode, Text Statistics
- Custom plugin creation with code editor
- INPUT variable injection, print() for output

### MemPalace
- Persistent memory storage for notes and observations
- Full-text search across notes and transmission history
- Tagging system for organization

### Model Switcher
- Per-agent model assignment
- 7 models across 3 providers:
  - OpenAI: GPT-5.2, GPT-5.1, GPT-4.1
  - Anthropic: Claude Sonnet 4.5, Claude Opus 4.5
  - Google: Gemini 3 Flash, Gemini 2.5 Pro

---

## Architecture

```
hermes-command-nexus/
+-- backend/
|   +-- server.py              # App entry, middleware, startup seeding (~80 lines)
|   +-- shared.py              # DB, clients, object storage, utilities
|   +-- routers/
|       +-- agents.py           # Agent CRUD
|       +-- dispatches.py       # Dispatch + SSE streaming
|       +-- voice.py            # Whisper STT + ElevenLabs TTS
|       +-- forge.py            # Gallery + async image gen + file proxy
|       +-- chains.py           # Chain CRUD + execution + templates
|       +-- plugins.py          # Plugin CRUD + server-side execution
|       +-- mempalace.py        # Notes CRUD + search
|       +-- system.py           # System info + models + operations log
|       +-- queue.py            # Offline dispatch queue
+-- frontend/
    +-- src/
        +-- App.js              # Main layout, nav, state management
        +-- components/
            +-- CommandCenter.jsx    # Dashboard with agent cards + system panel
            +-- DispatchConsole.jsx  # Terminal input + streaming + voice
            +-- AgentAvatar.jsx      # Animated hexagonal avatar
            +-- SystemPanel.jsx      # GPU / RAM / network stats
            +-- MemPalace.jsx        # Notes + search
            +-- ForgeGallery.jsx     # Image gallery + AI generation
            +-- ChainBuilder.jsx     # Drag-drop chain editor + templates
            +-- PluginManager.jsx    # Plugin CRUD + execution
            +-- ServiceRegistry.jsx  # Agent registration
            +-- ModelSwitcher.jsx    # Per-agent model assignment
            +-- OperationsLog.jsx    # Audit trail
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Tailwind CSS, shadcn/ui, Lucide icons |
| Backend | FastAPI, Motor (async MongoDB), Pydantic v2 |
| Database | MongoDB |
| AI (Text) | OpenAI GPT-5.2 via `emergentintegrations` |
| AI (Images) | GPT Image 1 + Gemini Nano Banana |
| Voice (STT) | OpenAI Whisper |
| Voice (TTS) | ElevenLabs (eleven_multilingual_v2) |
| Storage | Emergent Object Storage |
| Fonts | JetBrains Mono (headings/terminal), IBM Plex Sans (body) |

---

## Environment Variables

### Backend (`backend/.env`)

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=your_database_name
CORS_ORIGINS=*
EMERGENT_LLM_KEY=sk-emergent-xxxxx
ELEVENLABS_API_KEY=sk_xxxxx
```

### Frontend (`frontend/.env`)

```env
REACT_APP_BACKEND_URL=https://your-domain.com
```

---

## API Reference

### Agents
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/agents` | List all agents |
| POST | `/api/agents` | Register new agent |
| PATCH | `/api/agents/:id` | Update agent status/model |

### Dispatches
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/dispatches` | Create dispatch (synchronous) |
| POST | `/api/dispatches/stream` | Create dispatch (SSE streaming) |
| GET | `/api/dispatches` | List dispatches |

### Voice
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/voice/transcribe` | Speech-to-text (multipart audio) |
| POST | `/api/voice/speak` | Text-to-speech (returns base64 audio) |
| GET | `/api/voice/voices` | List available TTS voices |

### Forge & Image Generation
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/forge` | List gallery items |
| POST | `/api/forge` | Add manual item |
| POST | `/api/forge/generate` | Start async image generation (returns job_id) |
| GET | `/api/jobs/:id` | Poll job status |
| GET | `/api/files/:path` | Serve file from object storage |

### Chains & Templates
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/chains` | Create chain |
| GET | `/api/chains` | List chains |
| POST | `/api/chains/:id/execute` | Execute chain |
| GET | `/api/chain-templates` | List templates |
| POST | `/api/chain-templates/:id/use` | Clone template as chain |

### Plugins
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/plugins` | List plugins |
| POST | `/api/plugins` | Register plugin |
| POST | `/api/plugins/:id/execute` | Execute plugin |

### System
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/system` | System telemetry |
| GET | `/api/models` | Available LLM models |
| GET | `/api/operations` | Operations log |

### Offline Queue
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/queue` | Add to offline queue |
| GET | `/api/queue` | List queued items |
| POST | `/api/queue/flush` | Execute all queued dispatches |

---

## Design System

**Theme**: Dark terminal / command center aesthetic

| Token | Value | Usage |
|---|---|---|
| `--nexus-bg` | `#050505` | Base background |
| `--nexus-surface` | `#111111` | Panel background |
| `--nexus-green` | `#00FF41` | Primary accent, success states |
| `--nexus-cyan` | `#0EA5E9` | Secondary accent, info |
| `--nexus-yellow` | `#FFCC00` | Warning, busy states |
| `--nexus-red` | `#FF3333` | Error, critical |

- Zero rounded corners (`rounded-none`)
- 1px crisp borders
- Scanline overlay on terminal areas
- Monospace typography throughout

---

## License

MIT
"
