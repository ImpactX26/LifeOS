"""POST /ask end to end: FastAPI -> registry -> real MCP servers over HTTP -> engine."""
import json
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import main  # noqa: E402

pytestmark = pytest.mark.usefixtures("mcp_servers")
Q = {"question": "Can I afford a Goa trip next weekend?"}
CONTRACT = json.loads((ROOT / "contracts" / "verdict.after_finance.json").read_text(encoding="utf-8"))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "TODAY", date(2026, 10, 8))
    yield TestClient(main.app)
    main.registry.unplug("finance")


def test_finance_hot_plug_flips_the_answer(client):
    assert {s["name"]: s["plugged"] for s in client.get("/servers").json()["servers"]}["finance"] is False

    before = client.post("/ask", json=Q).json()
    assert before["verdict"]["verdict"] == "yes" and "finance" in before["verdict"]["not_read"]
    assert {t["server"] for t in before["trace"]} == {"calendar", "gmail", "travel"}

    client.post("/servers/finance/plug")
    after = client.post("/ask", json=Q).json()["verdict"]
    assert after["verdict"] == "yes_with_conditions" and after["numbers"] == CONTRACT["numbers"]


def test_bad_input(client):
    assert client.post("/servers/nope/plug").status_code == 404
    assert client.post("/ask", json={"question": ""}).status_code == 422
