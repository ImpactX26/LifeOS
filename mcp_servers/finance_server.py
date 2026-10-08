"""Finance MCP server on :8103 (streamable HTTP at /mcp).

No bank access: the balance is typed by the user, spending comes from the MASKED statement
(date, category, debit, credit only). Run:  .venv\\Scripts\\python mcp_servers\\finance_server.py
"""
import csv
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

DATA = Path(__file__).resolve().parents[1] / "data"
STATEMENT = DATA / "manu_statement.masked.csv"
BALANCE = DATA / "balance.json"
COST_TABLE = DATA / "cost_table.json"
FIXED = ["Rent (PG, incl. food)", "Investments (SIP)", "Subscriptions", "Phone"]  # PLAN §3: commitments
READ = ToolAnnotations(readOnlyHint=True)

mcp = FastMCP("finance", port=8103)


def _debits():
    with open(STATEMENT, encoding="utf-8") as f:
        return [(date.fromisoformat(r["date"]), r["category"], float(r["debit"])) for r in csv.DictReader(f) if r["debit"]]


@mcp.tool(annotations=READ)
def get_balance() -> dict:
    """Current bank balance as typed in by the user. LifeOS has no bank access."""
    return json.loads(BALANCE.read_text(encoding="utf-8"))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True))
def set_balance(amount: float) -> dict:
    """Record a new balance typed by the user. Write tool: LifeOS must get the user's approval first."""
    if not 0 <= amount < 1e9:  # also rejects NaN
        raise ValueError("amount must be between 0 and 1,000,000,000")
    record = {"balance": round(amount, 2), "currency": "INR", "as_of": date.today().isoformat(), "source": "user_entered"}
    BALANCE.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return {"success": True, **record}


@mcp.tool(annotations=READ)
def get_sips() -> dict:
    """Recurring SIP investments found in the statement: amount and day of month."""
    debits = _debits()
    months = defaultdict(set)
    for d, cat, amt in debits:
        if cat == "Investments (SIP)":
            months[(amt, d.day)].add(d.strftime("%Y-%m"))
    sips = [{"amount": a, "day_of_month": day, "months_seen": len(m)} for (a, day), m in sorted(months.items(), key=lambda x: x[0][1])]
    as_of = max(d for d, _, _ in debits).isoformat()
    return {"sips": sips, "monthly_total": sum(s["amount"] for s in sips), "source": "statement_csv", "as_of": as_of}


@mcp.tool(annotations=READ)
def get_spending_summary(days: int = 30) -> dict:
    """Spending by category over the last `days` days of the statement, plus monthly average spend and
    fixed monthly commitments (rent, SIPs, subscriptions, phone)."""
    if not 1 <= days <= 366:
        raise ValueError("days must be between 1 and 366")
    debits = _debits()
    end = max(d for d, _, _ in debits)
    start = end - timedelta(days=days - 1)
    window = defaultdict(float)
    for d, cat, amt in debits:
        if d >= start:
            window[cat] += amt
    # ponytail: assumes the statement covers whole calendar months (true for the fixture); prorate if partial months appear
    months = len({d.strftime("%Y-%m") for d, _, _ in debits})
    monthly = defaultdict(float)
    for _, cat, amt in debits:
        monthly[cat] += amt / months
    by_size = lambda d: {c: round(v, 2) for c, v in sorted(d.items(), key=lambda x: -x[1])}  # noqa: E731
    return {
        "period": {"from": start.isoformat(), "to": end.isoformat(), "days": days},
        "total_spend": round(sum(window.values()), 2),
        "by_category": by_size(window),
        "monthly_avg_spend": round(sum(monthly.values()), 2),
        "monthly_avg_by_category": by_size(monthly),
        "monthly_commitments": round(sum(monthly[c] for c in FIXED), 2),
        "commitment_categories": FIXED,
        "source": "statement_csv",
        "as_of": end.isoformat(),
    }


@mcp.tool(annotations=READ)
def get_cost_table() -> dict:
    """User-editable cost estimates (low/high) for trip items such as stay, food and local transport."""
    return json.loads(COST_TABLE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
