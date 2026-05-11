"""
Hermes Command Nexus - Tests for NEW features (iteration 2):
- SSE streaming dispatch
- Voice (TTS/STT/voices)
- Chains (CRUD + execute)
- Plugins (CRUD + execute, built-in seeded)
"""
import os
import io
import json
import base64
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://mempalace-hub.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    return s


@pytest.fixture(scope="session")
def agents(client):
    r = client.get(f"{API}/agents", timeout=20)
    assert r.status_code == 200
    return r.json()


# ----- SSE Streaming Dispatch -----
class TestStreamingDispatch:
    def test_stream_dispatch_events(self, client, agents):
        hermes = next(a for a in agents if a["name"] == "Hermes")
        payload = {"agent_id": hermes["id"], "prompt": "Reply with only: STREAM_OK"}
        with client.post(f"{API}/dispatches/stream", json=payload,
                         stream=True, timeout=120,
                         headers={"Accept": "text/event-stream"}) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers.get("content-type", "")
            event_types = []
            full_text = ""
            dispatch_id = None
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                data = json.loads(line[5:].strip())
                event_types.append(data.get("type"))
                if data.get("type") == "status":
                    dispatch_id = data.get("dispatch_id")
                if data.get("type") == "chunk":
                    full_text += data.get("content", "")
                if data.get("type") in ("complete", "error"):
                    break
            assert "status" in event_types, f"Missing status event. Got: {event_types}"
            assert "chunk" in event_types, f"Missing chunk events. Got: {event_types}"
            assert "complete" in event_types, f"Missing complete event. Got: {event_types}"
            assert dispatch_id, "dispatch_id missing"
            assert len(full_text) > 0, "No streamed content"

        # Verify dispatch persisted
        r2 = client.get(f"{API}/dispatches/{dispatch_id}", timeout=20)
        assert r2.status_code == 200
        d = r2.json()
        assert d["status"] == "completed"
        assert d["response"] and len(d["response"]) > 0

    def test_stream_invalid_agent(self, client):
        r = client.post(f"{API}/dispatches/stream",
                        json={"agent_id": "nonexistent", "prompt": "x"}, timeout=20)
        assert r.status_code == 404


# ----- Voice -----
class TestVoice:
    def test_voices_list(self, client):
        r = client.get(f"{API}/voice/voices", timeout=20)
        assert r.status_code == 200
        voices = r.json()
        assert isinstance(voices, list) and len(voices) > 0
        for v in voices:
            assert "voice_id" in v and "name" in v

    def test_tts_speak(self, client):
        payload = {"text": "Hermes online.", "voice_id": "JBFqnCBsd6RMkjVDRZzb"}
        r = client.post(f"{API}/voice/speak", json=payload, timeout=60)
        assert r.status_code == 200, f"TTS failed: {r.text}"
        data = r.json()
        assert "audio" in data
        assert data["audio"].startswith("data:audio/mpeg;base64,")
        b64 = data["audio"].split(",", 1)[1]
        raw = base64.b64decode(b64)
        assert len(raw) > 500, "Audio payload too small"

    def test_stt_transcribe_with_generated_audio(self, client):
        """Generate a small TTS audio sample then transcribe it."""
        # Get audio via TTS first (real audio bytes)
        tts = client.post(f"{API}/voice/speak",
                          json={"text": "Hello Hermes nexus.",
                                "voice_id": "JBFqnCBsd6RMkjVDRZzb"},
                          timeout=60)
        if tts.status_code != 200:
            pytest.skip("TTS unavailable; cannot generate test audio")
        audio_b64 = tts.json()["audio"].split(",", 1)[1]
        audio_bytes = base64.b64decode(audio_b64)

        files = {"audio_file": ("test.mp3", io.BytesIO(audio_bytes), "audio/mpeg")}
        r = client.post(f"{API}/voice/transcribe", files=files, timeout=60)
        # Whisper should succeed; if 500 returned we still want to surface it
        assert r.status_code == 200, f"Transcribe failed: {r.status_code} {r.text}"
        data = r.json()
        assert "text" in data
        assert isinstance(data["text"], str) and len(data["text"]) > 0


# ----- Chains -----
class TestChains:
    chain_id = None

    def test_create_chain(self, client, agents):
        hermes = next(a for a in agents if a["name"] == "Hermes")
        openclaw = next(a for a in agents if a["name"] == "OpenClaw")
        payload = {
            "name": "TEST_chain_pytest",
            "description": "Pytest 2-step chain",
            "steps": [
                {"agent_id": hermes["id"], "prompt_template": "Output a single short noun. Reply with only that noun."},
                {"agent_id": openclaw["id"], "prompt_template": "Write a 5-word slogan about: {input}"}
            ]
        }
        r = client.post(f"{API}/chains", json=payload, timeout=20)
        assert r.status_code == 200
        chain = r.json()
        assert chain["name"] == payload["name"]
        assert len(chain["steps"]) == 2
        assert "id" in chain
        assert "_id" not in chain
        TestChains.chain_id = chain["id"]

    def test_list_chains(self, client):
        r = client.get(f"{API}/chains", timeout=20)
        assert r.status_code == 200
        chains = r.json()
        assert any(c["id"] == TestChains.chain_id for c in chains)

    def test_execute_chain(self, client):
        if not TestChains.chain_id:
            pytest.skip("no chain id")
        r = client.post(f"{API}/chains/{TestChains.chain_id}/execute",
                        json={"input": "begin"}, timeout=180)
        assert r.status_code == 200, f"Execute failed: {r.text}"
        data = r.json()
        assert data["chain_id"] == TestChains.chain_id
        assert len(data["steps"]) == 2
        for step in data["steps"]:
            assert step.get("status") == "completed", f"Step failed: {step}"
            assert step.get("response")
        assert data.get("final_output")

    def test_delete_chain(self, client):
        if not TestChains.chain_id:
            pytest.skip("no chain id")
        r = client.delete(f"{API}/chains/{TestChains.chain_id}", timeout=20)
        assert r.status_code == 200
        r2 = client.delete(f"{API}/chains/{TestChains.chain_id}", timeout=20)
        assert r2.status_code == 404


# ----- Plugins -----
class TestPlugins:
    custom_plugin_id = None

    def test_builtin_plugins_seeded(self, client):
        r = client.get(f"{API}/plugins", timeout=20)
        assert r.status_code == 200
        plugins = r.json()
        builtins = [p for p in plugins if p.get("is_builtin")]
        names = [p["name"] for p in builtins]
        for expected in ["Word Counter", "JSON Formatter", "CSV to Table",
                         "Base64 Encode/Decode", "Text Statistics"]:
            assert expected in names, f"Built-in plugin missing: {expected} (got {names})"
        for p in plugins:
            assert "_id" not in p

    def test_execute_builtin_word_counter(self, client):
        r = client.get(f"{API}/plugins", timeout=20)
        wc = next(p for p in r.json() if p["name"] == "Word Counter")
        body = {"input_data": "one two three four five"}
        ex = client.post(f"{API}/plugins/{wc['id']}/execute", json=body, timeout=45)
        assert ex.status_code == 200
        data = ex.json()
        assert data["status"] == "success", f"Plugin failed: {data}"
        assert "Words: 5" in data["output"]
        assert data["exit_code"] == 0

    def test_create_custom_plugin(self, client):
        payload = {
            "name": "TEST_custom_echo",
            "description": "Echo input twice",
            "script": "print(INPUT)\nprint(INPUT)",
            "input_schema": "text",
            "output_schema": "text",
            "is_builtin": False
        }
        r = client.post(f"{API}/plugins", json=payload, timeout=20)
        assert r.status_code == 200
        p = r.json()
        assert p["name"] == payload["name"]
        assert p["is_builtin"] is False
        TestPlugins.custom_plugin_id = p["id"]

    def test_execute_custom_plugin(self, client):
        if not TestPlugins.custom_plugin_id:
            pytest.skip("no plugin id")
        r = client.post(f"{API}/plugins/{TestPlugins.custom_plugin_id}/execute",
                        json={"input_data": "PING"}, timeout=45)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert data["output"].count("PING") == 2

    def test_cannot_delete_builtin(self, client):
        r = client.get(f"{API}/plugins", timeout=20)
        builtin = next(p for p in r.json() if p.get("is_builtin"))
        d = client.delete(f"{API}/plugins/{builtin['id']}", timeout=20)
        assert d.status_code == 400

    def test_delete_custom_plugin(self, client):
        if not TestPlugins.custom_plugin_id:
            pytest.skip("no plugin id")
        d = client.delete(f"{API}/plugins/{TestPlugins.custom_plugin_id}", timeout=20)
        assert d.status_code == 200
        d2 = client.delete(f"{API}/plugins/{TestPlugins.custom_plugin_id}", timeout=20)
        assert d2.status_code == 404
