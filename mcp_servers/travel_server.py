"""Travel MCP server on :8104 (streamable HTTP at /mcp): one-way flight search.

Layers are live -> cached -> seeded, and every answer says which one it came from (source) and when (as_of).
ponytail: only the seeded layer exists so far; live SerpAPI + cached capture (D) slot in before it.
Run:  .venv\\Scripts\\python mcp_servers\\travel_server.py
"""
import json
from datetime import date as Date
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

SEEDED = Path(__file__).resolve().parents[1] / "data" / "flights_seeded.json"

mcp = FastMCP("travel", port=8104)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def search_flights(origin: str, dest: str, date: str) -> dict:
    """One-way flights between two airports (3-letter IATA codes) on an ISO date, with source and as_of."""
    origin, dest = origin.strip().upper(), dest.strip().upper()
    if not all(len(c) == 3 and c.isalpha() for c in (origin, dest)):
        raise ValueError("origin and dest must be 3-letter IATA airport codes")
    day = Date.fromisoformat(date).isoformat()
    data = json.loads(SEEDED.read_text(encoding="utf-8"))
    results = data["routes"].get(f"{origin}-{dest}-{day}", [])
    return {
        "origin": origin, "dest": dest, "date": day, "results": results,
        "source": data["source"], "as_of": data["as_of"],
        **({} if results else {"note": "no seeded fares for this route and date"}),
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
