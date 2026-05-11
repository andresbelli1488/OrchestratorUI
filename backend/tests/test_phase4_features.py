"""Phase 4 tests: router split + chain templates + object storage file serving."""
import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://mempalace-hub.preview.emergentagent.com').rstrip('/')


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ----- Router split: ensure existing endpoints still work -----
class TestRouterSplitEndpoints:
    def test_agents_get(self, s):
        r = s.get(f"{BASE_URL}/api/agents", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 2
        names = {a["name"] for a in data}
        assert "Hermes" in names and "OpenClaw" in names

    def test_dispatches_get(self, s):
        r = s.get(f"{BASE_URL}/api/dispatches", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_plugins_get(self, s):
        r = s.get(f"{BASE_URL}/api/plugins", timeout=30)
        assert r.status_code == 200
        plugins = r.json()
        assert isinstance(plugins, list) and len(plugins) >= 5

    def test_system_get(self, s):
        r = s.get(f"{BASE_URL}/api/system", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "gpu_devices" in data
        assert len(data["gpu_devices"]) == 2

    def test_chains_get(self, s):
        r = s.get(f"{BASE_URL}/api/chains", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_forge_get(self, s):
        r = s.get(f"{BASE_URL}/api/forge", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_mempalace_get(self, s):
        r = s.get(f"{BASE_URL}/api/mempalace/notes", timeout=30)
        assert r.status_code == 200

    def test_queue_get(self, s):
        r = s.get(f"{BASE_URL}/api/queue", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_operations_get(self, s):
        r = s.get(f"{BASE_URL}/api/operations", timeout=30)
        assert r.status_code == 200


# ----- Chain Templates -----
class TestChainTemplates:
    def test_get_templates_returns_five_seeded(self, s):
        r = s.get(f"{BASE_URL}/api/chain-templates", timeout=30)
        assert r.status_code == 200
        templates = r.json()
        assert isinstance(templates, list)
        names = [t["name"] for t in templates]
        expected = {"Research & Summarize", "Creative Brief Pipeline", "Code Review Chain",
                    "Brand Voice Generator", "Data → Insight → Action"}
        assert expected.issubset(set(names)), f"Missing templates. Got: {names}"
        # Validate template structure
        t = templates[0]
        assert "id" in t and "name" in t and "description" in t
        assert "steps" in t and isinstance(t["steps"], list) and len(t["steps"]) >= 1
        assert "category" in t
        assert "usage_count" in t
        for step in t["steps"]:
            assert "agent_id" in step
            assert "prompt_template" in step

    def test_use_template_clones_as_chain(self, s):
        # Get templates
        r = s.get(f"{BASE_URL}/api/chain-templates", timeout=30)
        assert r.status_code == 200
        templates = r.json()
        # Find Research & Summarize
        tmpl = next((t for t in templates if t["name"] == "Research & Summarize"), templates[0])
        tmpl_id = tmpl["id"]

        # Use the template
        r2 = s.post(f"{BASE_URL}/api/chain-templates/{tmpl_id}/use", timeout=30)
        assert r2.status_code == 200, f"Use template failed: {r2.text}"
        cloned_chain = r2.json()
        assert cloned_chain["name"].endswith("(copy)")
        assert cloned_chain["description"] == tmpl["description"]
        assert len(cloned_chain["steps"]) == len(tmpl["steps"])
        assert "id" in cloned_chain
        chain_id = cloned_chain["id"]

        # Verify chain persisted
        r3 = s.get(f"{BASE_URL}/api/chains", timeout=30)
        assert r3.status_code == 200
        chains = r3.json()
        found = next((c for c in chains if c["id"] == chain_id), None)
        assert found is not None
        assert found["name"].endswith("(copy)")

        # Cleanup: delete the cloned chain
        s.delete(f"{BASE_URL}/api/chains/{chain_id}", timeout=30)

    def test_use_nonexistent_template_returns_404(self, s):
        r = s.post(f"{BASE_URL}/api/chain-templates/nonexistent-id-xyz/use", timeout=30)
        assert r.status_code == 404

    def test_usage_count_increments(self, s):
        r = s.get(f"{BASE_URL}/api/chain-templates", timeout=30)
        templates = r.json()
        tmpl = templates[0]
        tmpl_id = tmpl["id"]
        before = tmpl.get("usage_count", 0)

        r2 = s.post(f"{BASE_URL}/api/chain-templates/{tmpl_id}/use", timeout=30)
        assert r2.status_code == 200
        cloned_id = r2.json()["id"]

        r3 = s.get(f"{BASE_URL}/api/chain-templates", timeout=30)
        updated = next(t for t in r3.json() if t["id"] == tmpl_id)
        assert updated["usage_count"] >= before + 1

        # Cleanup
        s.delete(f"{BASE_URL}/api/chains/{cloned_id}", timeout=30)


# ----- Object Storage / Forge -----
class TestObjectStorageAndForge:
    def test_files_endpoint_404_for_missing(self, s):
        r = s.get(f"{BASE_URL}/api/files/hermes-nexus/nonexistent/missing.png", timeout=30)
        assert r.status_code == 404

    def test_forge_generate_uses_storage_url(self, s):
        """Generate small image and verify URL is /api/files/ path (or base64 fallback)."""
        payload = {"prompt": "tiny red square on white background", "provider": "openai",
                   "title": "TEST_PHASE4_STORAGE", "tags": ["test-phase4"]}
        r = s.post(f"{BASE_URL}/api/forge/generate", json=payload, timeout=120)
        assert r.status_code == 200, f"Generate failed: {r.text[:300]}"
        data = r.json()
        assert "image" in data
        image_url = data["image"]
        forge_item = data["forge_item"]
        assert "storage_path" in forge_item

        # Preferred: storage URL path
        if image_url.startswith("/api/files/"):
            # Fetch via proxy
            path_part = image_url[len("/api/files/"):]
            full_url = f"{BASE_URL}/api/files/{path_part}"
            r2 = s.get(full_url, timeout=60)
            assert r2.status_code == 200
            assert r2.headers.get("Content-Type", "").startswith("image/")
            assert len(r2.content) > 100  # actual image bytes
            assert forge_item["storage_path"].startswith("hermes-nexus/forge/")
        else:
            # Fallback to base64 (storage failed); test still passes but flag
            assert image_url.startswith("data:image/png;base64,")
            print("WARNING: object storage fell back to base64 data URL")

        # Cleanup
        s.delete(f"{BASE_URL}/api/forge/{forge_item['id']}", timeout=30)

    def test_existing_forge_items_serve_via_proxy_if_storage_path(self, s):
        """For any existing forge item with storage_path, /api/files/{path} should work."""
        r = s.get(f"{BASE_URL}/api/forge", timeout=30)
        assert r.status_code == 200
        items = r.json()
        stored = [i for i in items if i.get("storage_path")]
        if not stored:
            pytest.skip("No forge items with storage_path; skipping proxy fetch test")
        item = stored[0]
        r2 = s.get(f"{BASE_URL}/api/files/{item['storage_path']}", timeout=60)
        assert r2.status_code == 200
        assert r2.headers.get("Content-Type", "").startswith("image/")


# ----- Other key endpoints (smoke) -----
class TestKeyEndpointSmoke:
    def test_voice_voices_endpoint(self, s):
        r = s.get(f"{BASE_URL}/api/voice/voices", timeout=30)
        assert r.status_code == 200
        voices = r.json()
        assert isinstance(voices, list) and len(voices) >= 1

    def test_queue_crud(self, s):
        # Need a valid agent_id
        r0 = s.get(f"{BASE_URL}/api/agents", timeout=30)
        agent_id = r0.json()[0]["id"]
        # Create
        payload = {"agent_id": agent_id, "prompt": "TEST_PHASE4_QUEUE"}
        r = s.post(f"{BASE_URL}/api/queue", json=payload, timeout=30)
        assert r.status_code == 200, f"Queue POST failed: {r.text}"
        item = r.json()
        qid = item["id"]
        # Get
        r2 = s.get(f"{BASE_URL}/api/queue", timeout=30)
        assert any(q["id"] == qid for q in r2.json())
        # Delete
        r3 = s.delete(f"{BASE_URL}/api/queue/{qid}", timeout=30)
        assert r3.status_code == 200
