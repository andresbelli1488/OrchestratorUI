"""
Hermes Command Nexus - Backend API tests
Covers: agents, dispatches, mempalace, forge, operations, system, models
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://mempalace-hub.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ----- Agents -----
class TestAgents:
    def test_get_agents_seeded(self, client):
        r = client.get(f"{API}/agents", timeout=20)
        assert r.status_code == 200
        agents = r.json()
        assert isinstance(agents, list)
        names = [a["name"] for a in agents]
        assert "Hermes" in names, f"Hermes missing. Got: {names}"
        assert "OpenClaw" in names, f"OpenClaw missing. Got: {names}"
        for a in agents:
            assert "id" in a and "status" in a and "preferred_model" in a
            assert "_id" not in a

    def test_update_agent_model(self, client):
        agents = client.get(f"{API}/agents", timeout=20).json()
        hermes = next(a for a in agents if a["name"] == "Hermes")
        original = hermes["preferred_model"]
        r = client.patch(f"{API}/agents/{hermes['id']}",
                         json={"preferred_model": "gpt-5.1", "preferred_provider": "openai"},
                         timeout=20)
        assert r.status_code == 200
        assert r.json()["preferred_model"] == "gpt-5.1"
        # restore
        client.patch(f"{API}/agents/{hermes['id']}",
                     json={"preferred_model": original, "preferred_provider": "openai"}, timeout=20)


# ----- System / Models -----
class TestSystemModels:
    def test_system_info(self, client):
        r = client.get(f"{API}/system", timeout=20)
        assert r.status_code == 200
        data = r.json()
        for k in ["gpu_devices", "ram", "network", "agent_count", "dispatch_count", "note_count", "forge_count", "recent_operations"]:
            assert k in data, f"Missing key: {k}"
        assert isinstance(data["gpu_devices"], list) and len(data["gpu_devices"]) >= 1
        assert "used" in data["ram"] and "total" in data["ram"]

    def test_models(self, client):
        r = client.get(f"{API}/models", timeout=20)
        assert r.status_code == 200
        models = r.json()
        assert isinstance(models, list) and len(models) > 0
        assert any(m["model"] == "gpt-5.2" for m in models)
        for m in models:
            assert {"provider", "model", "label"}.issubset(m.keys())


# ----- MemPalace -----
class TestMemPalace:
    note_id = None

    def test_create_note(self, client):
        payload = {"content": "TEST_note_for_pytest hermes nexus", "tags": ["TEST", "pytest"]}
        r = client.post(f"{API}/mempalace/notes", json=payload, timeout=20)
        assert r.status_code == 200
        note = r.json()
        assert note["content"] == payload["content"]
        assert "id" in note
        TestMemPalace.note_id = note["id"]

    def test_list_notes_includes_created(self, client):
        r = client.get(f"{API}/mempalace/notes", timeout=20)
        assert r.status_code == 200
        notes = r.json()
        assert any(n["id"] == TestMemPalace.note_id for n in notes)

    def test_search_mempalace(self, client):
        r = client.get(f"{API}/mempalace/search", params={"q": "TEST_note_for_pytest"}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "notes" in data and "transmissions" in data
        assert any(n["id"] == TestMemPalace.note_id for n in data["notes"])

    def test_delete_note(self, client):
        if not TestMemPalace.note_id:
            pytest.skip("no note id")
        r = client.delete(f"{API}/mempalace/notes/{TestMemPalace.note_id}", timeout=20)
        assert r.status_code == 200
        # verify removed
        r2 = client.delete(f"{API}/mempalace/notes/{TestMemPalace.note_id}", timeout=20)
        assert r2.status_code == 404


# ----- Forge -----
class TestForge:
    item_id = None

    def test_create_forge_item(self, client):
        payload = {"title": "TEST_forge_item", "type": "image", "url": "https://example.com/x.png",
                   "tags": ["TEST"], "source_agent": "Hermes", "description": "pytest item"}
        r = client.post(f"{API}/forge", json=payload, timeout=20)
        assert r.status_code == 200
        item = r.json()
        assert item["title"] == payload["title"]
        TestForge.item_id = item["id"]

    def test_list_forge_items(self, client):
        r = client.get(f"{API}/forge", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert any(i["id"] == TestForge.item_id for i in items)

    def test_delete_forge(self, client):
        if not TestForge.item_id:
            pytest.skip("no id")
        r = client.delete(f"{API}/forge/{TestForge.item_id}", timeout=20)
        assert r.status_code == 200


# ----- Operations -----
class TestOperations:
    def test_operations_log(self, client):
        r = client.get(f"{API}/operations", timeout=20)
        assert r.status_code == 200
        ops = r.json()
        assert isinstance(ops, list)
        if ops:
            assert {"action", "timestamp", "status"}.issubset(ops[0].keys())


# ----- Dispatch (calls real GPT) -----
class TestDispatch:
    def test_dispatch_to_hermes(self, client):
        agents = client.get(f"{API}/agents", timeout=20).json()
        hermes = next(a for a in agents if a["name"] == "Hermes")
        r = client.post(f"{API}/dispatches",
                        json={"agent_id": hermes["id"], "prompt": "Reply with the single word: ACKNOWLEDGED"},
                        timeout=120)
        assert r.status_code == 200, f"Dispatch failed: {r.text}"
        d = r.json()
        assert d["agent_id"] == hermes["id"]
        assert d["status"] in ("completed", "failed"), f"Unexpected status: {d}"
        if d["status"] == "failed":
            pytest.fail(f"Dispatch failed: {d.get('response')}")
        assert d["response"] and len(d["response"]) > 0

    def test_dispatch_invalid_agent(self, client):
        r = client.post(f"{API}/dispatches", json={"agent_id": "nonexistent-id", "prompt": "x"}, timeout=20)
        assert r.status_code == 404

    def test_list_dispatches(self, client):
        r = client.get(f"{API}/dispatches?limit=5", timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
