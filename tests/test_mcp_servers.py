import asyncio
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp_servers"))
import calendar_server  # noqa: E402
import finance_server  # noqa: E402
import gmail_server  # noqa: E402

LOCKED = {
    "calendar": {"list_events", "find_free_slots"},
    "gmail": {"list_tasks", "get_deadlines"},
    "finance": {"get_balance", "set_balance", "get_sips", "get_spending_summary", "get_cost_table"},
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    # Tests never touch Google: force the seeded fallback.
    monkeypatch.setattr(calendar_server, "creds", lambda: None)
    monkeypatch.setattr(gmail_server, "creds", lambda: None)


def test_locked_tool_names_and_write_flags():
    for server in (calendar_server, gmail_server, finance_server):
        tools = asyncio.run(server.mcp.list_tools())
        assert {t.name for t in tools} == LOCKED[server.mcp.name]
        writes = {t.name for t in tools if not t.annotations.readOnlyHint}
        assert writes == ({"set_balance"} if server.mcp.name == "finance" else set())


def test_finance_numbers():
    s = finance_server.get_spending_summary(30)
    assert s["monthly_avg_spend"] == 46319.5
    assert s["monthly_commitments"] == 15617
    assert s["period"] == {"from": "2026-09-01", "to": "2026-09-30", "days": 30}
    assert finance_server.get_sips()["sips"] == [
        {"amount": 3000, "day_of_month": 10, "months_seen": 2},
        {"amount": 2000, "day_of_month": 15, "months_seen": 2},
    ]
    assert finance_server.get_balance()["balance"] == 21842


def test_set_balance_validates_and_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(finance_server, "BALANCE", tmp_path / "balance.json")
    for bad in (-1, float("nan"), 1e12):
        with pytest.raises(ValueError):
            finance_server.set_balance(bad)
    finance_server.set_balance(25000)
    assert json.loads((tmp_path / "balance.json").read_text())["balance"] == 25000


def test_calendar_weekend_free_after_friday_party():
    r = calendar_server.find_free_slots("2026-10-10", "2026-10-11", 60)
    assert r["source"] == "seeded"
    assert r["slots"] == [{"start": "2026-10-10T00:30:00+05:30", "end": "2026-10-12T00:00:00+05:30", "minutes": 2850}]
    titles = [e["title"] for e in calendar_server.list_events("2026-10-09", "2026-10-09")["events"]]
    assert titles == ["Team lunch", "Friday party - Skyline Brewpub"]


def test_gmail_returns_only_deadline_emails_masked():
    r = gmail_server.list_tasks()
    assert [t["deadline"][:10] for t in r["tasks"]] == ["2026-10-09", "2026-10-12", "2026-10-12", "2026-10-20"]
    text = json.dumps(r)
    for leak in ("@", "778812345", "Swiggy", "Meghana"):  # addresses, policy number, non-task email
        assert leak not in text
    # The injection arrives as plain data; Guardian (not this server) stops the set_balance call.
    assert any("Ignore all previous instructions" in t["snippet"] for t in r["tasks"])


def test_gmail_deadline_formats():
    assert gmail_server._deadline("Q3 report - due 12th October 2026, 10:00").isoformat() == "2026-10-12T10:00:00+05:30"
    assert gmail_server._deadline("Deadline: 12 Oct 2026").isoformat() == "2026-10-12T23:59:00+05:30"
    assert gmail_server._deadline("due 31 Feb 2026") is None
    assert gmail_server._deadline("no date here") is None


def test_gmail_deadlines_in_range():
    r = gmail_server.get_deadlines("2026-10-10", "2026-10-12")
    assert [(t["title"], t["deadline"]) for t in r["tasks"]] == [
        ("Q3 quarterly report - due 12 Oct 2026, 10:00", "2026-10-12T10:00:00+05:30"),
        ("Book your Tuesday badminton court", "2026-10-12T20:00:00+05:30"),
    ]
