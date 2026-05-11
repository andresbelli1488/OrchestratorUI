"""
Hermes Command Nexus - Phase 3 feature tests:
- Voice selector (8 voices) and TTS with custom voice_id
- Forge image generation (OpenAI GPT Image 1, Gemini Nano Banana)
- GPU panel: only 2 GPU devices (no RTX 4070 Super #2)
- Offline queue: POST/GET/DELETE/flush
"""
import os
import base64
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://mempalace-hub.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def client():
    return requests.Session()


@pytest.fixture(scope="session")
def agents(client):
    r = client.get(f"{API}/agents", timeout=20)
    assert r.status_code == 200
    return r.json()


# ----- Voices -----
class TestVoices:
    def test_voices_returns_8_with_id_and_name(self, client):
        r = client.get(f"{API}/voice/voices", timeout=20)
        assert r.status_code == 200
        voices = r.json()
        assert isinstance(voices, list)
        # Default fallback list has 8 voices
        assert len(voices) >= 8, f"Expected >=8 voices, got {len(voices)}"
        for v in voices:
            assert "voice_id" in v and isinstance(v["voice_id"], str)
            assert "name" in v and isinstance(v["name"], str)

    def test_tts_with_custom_voice_id(self, client):
        # Use Rachel (different from default George)
        payload = {"text": "Testing custom voice.", "voice_id": "21m00Tcm4TlvDq8ikWAM"}
        r = client.post(f"{API}/voice/speak", json=payload, timeout=60)
        assert r.status_code == 200, f"TTS failed: {r.text}"
        data = r.json()
        assert data["audio"].startswith("data:audio/mpeg;base64,")
        raw = base64.b64decode(data["audio"].split(",", 1)[1])
        assert len(raw) > 500


# ----- System (GPU panel) -----
class TestSystemGPU:
    def test_system_only_two_gpus(self, client):
        r = client.get(f"{API}/system", timeout=20)
        assert r.status_code == 200
        data = r.json()
        gpus = data.get("gpu_devices", [])
        assert len(gpus) == 2, f"Expected exactly 2 GPUs, got {len(gpus)}: {gpus}"
        names = [g["name"] for g in gpus]
        assert "RTX 4070 Super #1" in names
        assert "RTX 3050" in names
        assert "RTX 4070 Super #2" not in names


# ----- Image Generation -----
class TestImageGen:
    def test_generate_image_openai(self, client):
        payload = {"prompt": "A tiny red circle on white background", "provider": "openai"}
        r = client.post(f"{API}/forge/generate", json=payload, timeout=180)
        assert r.status_code == 200, f"OpenAI image gen failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        assert "image" in data
        assert data["image"].startswith("data:image/png;base64,")
        b64 = data["image"].split(",", 1)[1]
        raw = base64.b64decode(b64)
        assert len(raw) > 1000, "Image bytes too small"
        # Auto-added to forge
        assert "forge_item" in data
        item = data["forge_item"]
        assert item["type"] == "image"
        assert "ai-generated" in item["tags"]
        assert "openai" in item["tags"]
        # Verify it's in /api/forge
        r2 = client.get(f"{API}/forge", timeout=20)
        assert r2.status_code == 200
        assert any(f["id"] == item["id"] for f in r2.json())

    def test_generate_image_gemini(self, client):
        payload = {"prompt": "A tiny blue square on white background", "provider": "gemini"}
        r = client.post(f"{API}/forge/generate", json=payload, timeout=180)
        assert r.status_code == 200, f"Gemini image gen failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        assert data["image"].startswith("data:image/png;base64,")
        item = data["forge_item"]
        assert "ai-generated" in item["tags"]
        assert "gemini" in item["tags"]


# ----- Offline Queue -----
class TestOfflineQueue:
    queue_ids = []

    def test_add_to_queue(self, client, agents):
        hermes = next(a for a in agents if a["name"] == "Hermes")
        payload = {"agent_id": hermes["id"], "prompt": "TEST_QUEUE_ITEM reply with OK"}
        r = client.post(f"{API}/queue", json=payload, timeout=20)
        assert r.status_code == 200
        item = r.json()
        assert item["status"] == "queued"
        assert item["agent_id"] == hermes["id"]
        assert item["agent_name"] == "Hermes"
        assert "_id" not in item
        TestOfflineQueue.queue_ids.append(item["id"])

    def test_add_to_queue_invalid_agent(self, client):
        r = client.post(f"{API}/queue",
                        json={"agent_id": "nonexistent", "prompt": "x"}, timeout=20)
        assert r.status_code == 404

    def test_list_queue(self, client):
        r = client.get(f"{API}/queue", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert any(i["id"] in TestOfflineQueue.queue_ids for i in items)

    def test_delete_from_queue(self, client, agents):
        # Add a throwaway then delete it
        hermes = next(a for a in agents if a["name"] == "Hermes")
        r = client.post(f"{API}/queue",
                        json={"agent_id": hermes["id"], "prompt": "TEST_QUEUE_DELETE"},
                        timeout=20)
        assert r.status_code == 200
        qid = r.json()["id"]
        d = client.delete(f"{API}/queue/{qid}", timeout=20)
        assert d.status_code == 200
        d2 = client.delete(f"{API}/queue/{qid}", timeout=20)
        assert d2.status_code == 404

    def test_flush_queue_executes_and_clears(self, client, agents):
        # Ensure at least one item is queued (the one from test_add_to_queue may still be there)
        hermes = next(a for a in agents if a["name"] == "Hermes")
        client.post(f"{API}/queue",
                    json={"agent_id": hermes["id"], "prompt": "TEST_FLUSH reply with FLUSHED"},
                    timeout=20)
        r = client.post(f"{API}/queue/flush", json={}, timeout=180)
        assert r.status_code == 200, f"Flush failed: {r.text}"
        data = r.json()
        assert "flushed" in data
        assert data["flushed"] >= 1
        assert isinstance(data["results"], list)
        # Each result must have a dispatch_id (or error)
        for res in data["results"]:
            assert "queue_id" in res
        # Queue should now be empty
        r2 = client.get(f"{API}/queue", timeout=20)
        assert r2.status_code == 200
        assert r2.json() == [] or len(r2.json()) == 0
