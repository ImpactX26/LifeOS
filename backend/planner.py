"""Rules planner: question -> trip + which tools to call with which arguments. No LLM.

This is the always-works fallback; the Gemini agent becomes the primary planner later.
It never names a server: arguments are filled from each tool's parameter names, and only
tools marked read-only are ever planned (writes need Guardian + the user's approval).
"""
from datetime import timedelta

HOME = "BLR"  # ponytail: Manu's home airport; the optional Location server would supply this
AIRPORTS = {"goa": "GOI", "mumbai": "BOM", "delhi": "DEL", "chennai": "MAA", "hyderabad": "HYD", "kochi": "COK", "jaipur": "JAI"}


def parse_trip(question, today):
    """{"city", "origin", "dest", "start", "end"} for a weekend trip, or None if no known destination."""
    q = question.lower()
    city = next((c for c in AIRPORTS if c in q), None)
    if city is None:
        return None
    # PLAN P2: "this weekend" / "next weekend" both mean the upcoming Saturday-Sunday (never today)
    start = today + timedelta(days=(5 - today.weekday()) % 7 or 7)
    return {"city": city.title(), "origin": HOME, "dest": AIRPORTS[city], "start": start, "end": start + timedelta(days=1)}


def plan(question, tools, today):
    """(trip, [(tool_name, args), ...]) using the discovered catalogue from registry.discover()."""
    trip = parse_trip(question, today)
    if trip is None:
        return None, []
    context = {"start": today.isoformat(), "end": (trip["end"] + timedelta(days=1)).isoformat(), "min_minutes": 60, "days": 30}
    calls = []
    for t in tools:
        if not t["read_only"]:
            continue
        params = set(t["input_schema"].get("properties", {}))
        if {"origin", "dest", "date"} <= params:  # a route search: there and back
            calls.append((t["name"], {"origin": trip["origin"], "dest": trip["dest"], "date": trip["start"].isoformat()}))
            calls.append((t["name"], {"origin": trip["dest"], "dest": trip["origin"], "date": trip["end"].isoformat()}))
        elif params <= set(context):
            calls.append((t["name"], {p: context[p] for p in params}))
    return trip, calls
