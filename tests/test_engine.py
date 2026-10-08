"""Planner + engine against the real server functions (in-process, seeded data). No network."""
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "mcp_servers")]
import calendar_server  # noqa: E402
import engine  # noqa: E402
import finance_server  # noqa: E402
import gmail_server  # noqa: E402
import planner  # noqa: E402
import travel_server  # noqa: E402

Q = "Can I afford a Goa trip next weekend?"
TODAY = date(2026, 10, 8)
KNOWN = ["calendar", "gmail", "travel", "finance"]
CONTRACT = json.loads((ROOT / "contracts" / "verdict.after_finance.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(calendar_server, "creds", lambda: None)
    monkeypatch.setattr(gmail_server, "creds", lambda: None)


def ask(question, servers):
    """What POST /ask does, minus HTTP: discover -> plan -> call -> decide."""
    tools, fns = [], {}
    for mod in servers:
        for t in asyncio.run(mod.mcp.list_tools()):
            name = f"{mod.mcp.name}__{t.name}"
            tools.append({"name": name, "input_schema": t.inputSchema, "read_only": bool(t.annotations.readOnlyHint)})
            fns[name] = getattr(mod, t.name)
    trip, calls = planner.plan(question, tools, TODAY)
    results = [{"server": n.split("__")[0], "tool": n.split("__")[1], "args": a, "ok": True, "result": fns[n](**a), "ms": 0}
               for n, a in calls]
    return engine.decide(question, trip, results, KNOWN), calls


def test_planner_dates_directions_and_no_writes():
    trip = planner.parse_trip(Q, TODAY)
    assert (trip["start"], trip["end"], trip["dest"]) == (date(2026, 10, 10), date(2026, 10, 11), "GOI")
    _, calls = ask(Q, [calendar_server, gmail_server, travel_server, finance_server])
    names = [n for n, _ in calls]
    assert "finance__set_balance" not in names
    assert [a for n, a in calls if n == "travel__search_flights"] == [
        {"origin": "BLR", "dest": "GOI", "date": "2026-10-10"},
        {"origin": "GOI", "dest": "BLR", "date": "2026-10-11"},
    ]


def test_before_finance_looks_fine():
    v, _ = ask(Q, [calendar_server, gmail_server, travel_server])
    assert v["verdict"] == "yes" and v["not_read"] == ["finance"]
    assert v["numbers"]["trip_cost"] == {"low": 8109, "high": 13000} and v["numbers"]["balance"] is None
    findings = " | ".join(e["finding"] for e in v["evidence"])
    assert "1 email contains instructions aimed at the AI" in findings
    assert not any("Goa weekend pre-approval" in t for t in v["tradeoffs"])  # injected email never shapes the plan
    assert any("Q3 quarterly report" in t for t in v["tradeoffs"])


def test_after_finance_matches_contract():
    v, _ = ask(Q, [calendar_server, gmail_server, travel_server, finance_server])
    assert v["verdict"] == CONTRACT["verdict"] and v["numbers"] == CONTRACT["numbers"]
    assert v["headline"].startswith("Only if you skip club nights, parties and dinners out this month.")
    assert v["not_read"] == []
    assert v["tradeoffs"][:3] == [
        "Skip club nights this month: frees ~Rs 9,350",
        "Skip parties this month: frees ~Rs 3,995",
        "Skip dinners out this month: frees ~Rs 3,150",
    ]
    assert "Your SIPs (Rs 5,000/mo) stay untouched" in v["tradeoffs"]


@pytest.mark.parametrize("balance, verdict", [(200000, "yes"), (0, "no")])
def test_balance_extremes(tmp_path, monkeypatch, balance, verdict):
    path = tmp_path / "balance.json"
    path.write_text(json.dumps({"balance": balance, "currency": "INR", "as_of": "2026-10-08", "source": "user_entered"}))
    monkeypatch.setattr(finance_server, "BALANCE", path)
    v, _ = ask(Q, [calendar_server, gmail_server, travel_server, finance_server])
    assert v["verdict"] == verdict


def test_non_trip_question_is_honest():
    v, calls = ask("Should I learn guitar?", [calendar_server, finance_server])
    assert v["verdict"] == "insufficient_data" and calls == []
