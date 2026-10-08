"""Travel MCP server on :8104 (streamable HTTP at /mcp): one-way flight search.

Layers, always labelled with source + as_of:
  cached  a live answer from the last CACHE_MINUTES: instant and saves the small SerpAPI quota
  live    SerpAPI Google Flights (needs SERPAPI_API_KEY in .env); every live answer is saved to the cache
  cached  an older cached answer, if live fails
  seeded  data/flights_seeded.json, the last resort (hand-made demo fares, never called live)
Run:  .venv\\Scripts\\python mcp_servers\\travel_server.py
"""
import json
import logging
import os
from datetime import date as Date
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
IST = timezone(timedelta(hours=5, minutes=30))
SEEDED = ROOT / "data" / "flights_seeded.json"
CACHE = ROOT / "data" / "flights_cache.json"
SERPAPI = "https://serpapi.com/search"
CACHE_MINUTES = 60
TIMEOUT_S = 8  # under the registry's 10 s, so a slow search still falls back instead of timing out
MAX_FARES = 5  # ponytail: "high" = 5th-cheapest fare, so one odd premium fare can't inflate the range

mcp = FastMCP("travel", port=8104 + int(os.getenv("LIFEOS_PORT_OFFSET", "0")))  # tests use their own ports
# httpx logs every request URL at INFO, and SerpAPI's key lives in the URL. Never let it reach a log.
logging.getLogger("httpx").setLevel(logging.WARNING)


def _read(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"routes": {}}


def _fares(data):
    """SerpAPI Google Flights JSON -> [{airline, depart, arrive, price, stops}], cheapest first, any number of stops."""
    fares = []
    for offer in data.get("best_flights", []) + data.get("other_flights", []):
        legs = offer.get("flights") or []
        if not legs or not offer.get("price"):
            continue
        fares.append({
            "airline": legs[0].get("airline", "?"),
            "depart": legs[0]["departure_airport"]["time"][-5:],  # "YYYY-MM-DD HH:MM" -> "HH:MM"
            "arrive": legs[-1]["arrival_airport"]["time"][-5:],
            "price": int(offer["price"]),
            "stops": len(legs) - 1,
        })
    # stops count too: abroad the nonstop can cost 3x a one-stop (BLR-NRT tomorrow: Rs 1.59 lakh vs far less via SIN)
    return sorted(fares, key=lambda f: f["price"])[:MAX_FARES]


async def _live(origin, dest, day):
    """(fares, None) or (None, why). Never puts the exception text in `why`: the request URL contains the key."""
    key = os.getenv("SERPAPI_API_KEY")
    if os.getenv("LIFEOS_OFFLINE") or not key:
        return None, "live search off (LIFEOS_OFFLINE set or no SERPAPI_API_KEY)"
    params = {"engine": "google_flights", "departure_id": origin, "arrival_id": dest, "outbound_date": day,
              "type": "2", "currency": "INR", "hl": "en", "gl": "in", "api_key": key}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            r = await client.get(SERPAPI, params=params)
        data = r.json()
    except Exception as e:
        return None, f"SerpAPI unreachable ({type(e).__name__})"
    if r.status_code != 200 or "error" in data:
        return None, f"SerpAPI {r.status_code}: {str(data.get('error', ''))[:80]}"
    fares = _fares(data)
    return (fares, None) if fares else (None, "SerpAPI found no flights")


def _answer(origin, dest, day, results, source, as_of, note=None):
    return {"origin": origin, "dest": dest, "date": day, "results": results, "source": source, "as_of": as_of,
            **({"note": note} if note else {})}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
async def search_flights(origin: str, dest: str, date: str) -> dict:
    """One-way flights between two airports (3-letter IATA codes) on an ISO date, cheapest first.
    Every answer says where the prices came from (source: live | cached | seeded) and when (as_of)."""
    origin, dest = origin.strip().upper(), dest.strip().upper()
    if not all(len(c) == 3 and c.isalpha() for c in (origin, dest)):
        raise ValueError("origin and dest must be 3-letter IATA airport codes")
    day = Date.fromisoformat(date).isoformat()
    route = f"{origin}-{dest}-{day}"
    now = datetime.now(IST)

    hit = _read(CACHE)["routes"].get(route)
    if hit and now - datetime.fromisoformat(hit["as_of"]) < timedelta(minutes=CACHE_MINUTES):
        return _answer(origin, dest, day, hit["results"], "cached", hit["as_of"])

    fares, why = await _live(origin, dest, day)
    if fares:
        as_of = now.isoformat(timespec="seconds")
        cache = _read(CACHE)  # no await between read and write, so parallel calls can't lose each other's entry
        cache["routes"][route] = {"as_of": as_of, "results": fares}
        tmp = CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
        tmp.replace(CACHE)
        return _answer(origin, dest, day, fares, "live", as_of)
    if hit:
        return _answer(origin, dest, day, hit["results"], "cached", hit["as_of"], why)
    seeded = _read(SEEDED)
    results = seeded["routes"].get(route, [])
    return _answer(origin, dest, day, results, "seeded", seeded.get("as_of", ""),
                   why if results else f"{why}; no seeded fares for this route and date")


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
