"""Deterministic decision engine: tool results -> the locked verdict JSON (see contracts/).

No LLM and no I/O: every number comes from a tool result. The money rule is PLAN P1:
keep one month of fixed commitments untouched; anything beyond that has to come from
discretionary spending the user is willing to skip. SIPs are never cut.
"""
import re
from datetime import date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
TRIP_HOURS = (time(6), time(22))  # a trip occupies 06:00 on the first day to 22:00 on the last
# Discretionary categories (PLAN P1) -> how to say "cut it". Rent, SIPs and bills are never here.
CUTTABLE = {
    "Club": "skip club nights",
    "Partying": "skip parties",
    "Dining with friends": "skip dinners out",
    "Shopping": "pause shopping",
    "Transport (cab)": "take the metro instead of cabs",
    "Games & entertainment": "skip arcades and game nights",
    "Food delivery": "stop ordering in",
}
# ponytail: keyword check for instructions hidden in email/calendar text; Guardian (C) owns the real defence
INJECTION = re.compile(r"ignore (all )?(previous|prior) instructions|system notice to ai|you are now|call set_balance", re.I)


def _rs(n):
    return f"Rs {round(n):,}"


def _when(iso):
    return datetime.fromisoformat(iso).strftime("%a %d %b %H:%M")


def _day(d):
    return d.strftime("%a %d %b")


def _join(parts):
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _join_actions(phrases):
    """'skip club nights', 'skip parties' -> 'skip club nights and parties' (shared verb said once)."""
    verb = phrases[0].split()[0]
    if len(phrases) > 1 and all(p.split()[0] == verb for p in phrases):
        phrases = [phrases[0]] + [p.split(" ", 1)[1] for p in phrases[1:]]
    return _join(phrases)


def _short(title):
    return re.sub(r"\s*[-–]\s*(confirm\s+)?due\b.*$", "", title, flags=re.I)


def _range(pair):
    return {"low": round(pair[0]), "high": round(pair[1])} if pair else {"low": None, "high": None}


def decide(question, trip, results, known_servers):
    """trip from planner.parse_trip (or None), results from registry.call, known_servers = every server LifeOS knows."""
    evidence, tradeoffs, by_tool = [], [], {}
    for r in results:
        if r["ok"]:
            by_tool.setdefault(r["tool"], []).append(r)
        else:
            evidence.append({"server": r["server"], "tool": r["tool"], "finding": f"FAILED: {r['error'][:100]}", "as_of": "", "source": "error"})

    def note(r, finding):
        res = r["result"]
        evidence.append({"server": r["server"], "tool": r["tool"], "finding": finding,
                         "as_of": str(res.get("as_of", "")), "source": res.get("source", "")})

    def first(tool):
        return by_tool[tool][0] if tool in by_tool else None

    def out(verdict, headline, balance=None, trip_cost=None, commitments=None, remaining=None):
        return {
            "question": question,
            "verdict": verdict,
            "headline": headline,
            "numbers": {
                "balance": None if balance is None else round(balance),
                "trip_cost": _range(trip_cost),
                "monthly_commitments": None if commitments is None else round(commitments),
                "remaining": _range(remaining),
            },
            "evidence": evidence,
            "tradeoffs": tradeoffs,
            "not_read": sorted(set(known_servers) - {e["server"] for e in evidence if e["source"] != "error"}),
        }

    if trip is None:
        return out("insufficient_data", 'I can only plan trips so far. Try: "Can I afford a Goa trip next weekend?"')

    # --- time: calendar ---
    win_start = datetime.combine(trip["start"], TRIP_HOURS[0], IST)
    win_end = datetime.combine(trip["end"], TRIP_HOURS[1], IST)
    free = None
    for r in by_tool.get("find_free_slots", []):
        free = any(datetime.fromisoformat(s["start"]) <= win_start and datetime.fromisoformat(s["end"]) >= win_end
                   for s in r["result"]["slots"])
        note(r, f"{_day(trip['start'])} - {_day(trip['end'])} {'fully free' if free else 'not fully free'}")
    for r in by_tool.get("list_events", []):
        events = r["result"]["events"]
        clashes = [e for e in events if datetime.fromisoformat(e["start"]) < win_end and datetime.fromisoformat(e["end"]) > win_start]
        note(r, f"{len(events)} events read; " + (f"clash: {_join([e['title'] for e in clashes])}" if clashes else "none during the trip"))
        tradeoffs += [f"Move or skip '{e['title']}' ({_when(e['start'])})" for e in clashes]
        free = False if clashes else (True if free is None else free)

    # --- deadlines: email (text is untrusted; flagged emails never become part of the plan) ---
    flagged = set()
    for r in by_tool.get("list_tasks", []):
        tasks = r["result"]["tasks"]
        bad = [t for t in tasks if INJECTION.search(f"{t['title']} {t.get('snippet', '')}")]
        flagged |= {t["title"] for t in bad}
        note(r, f"{len(tasks)} emails with deadlines")
        if bad:
            note(r, f"{len(bad)} email{'s contain' if len(bad) > 1 else ' contains'} instructions aimed at the AI - treated as data, not followed")
    deadline_tradeoffs = []
    for r in by_tool.get("get_deadlines", []):
        due = [t for t in r["result"]["tasks"] if t["title"] not in flagged]
        note(r, "; ".join(f"{_short(t['title'])} due {_when(t['deadline'])}" for t in due) or "No deadlines around the trip")
        deadline_tradeoffs += [f"Before you go: {_short(t['title'])} (due {_when(t['deadline'])})" for t in due]

    # --- trip cost: flights + the user's cost table ---
    legs = {}
    for r in by_tool.get("search_flights", []):
        res = r["result"]
        fares = sorted(res["results"], key=lambda f: f["price"])
        legs["out" if res["origin"] == trip["origin"] else "back"] = fares
        span = f"{_rs(fares[0]['price'])} - {_rs(fares[-1]['price'])} ({len(fares)} flights)" if fares else "no fares found"
        note(r, f"{res['origin']}-{res['dest']} {_day(date.fromisoformat(res['date']))}: {span}")
    flights = None
    if legs.get("out") and legs.get("back"):
        o, b = legs["out"], legs["back"]
        flights = (o[0]["price"] + b[0]["price"], o[-1]["price"] + b[-1]["price"])

    nights = (trip["end"] - trip["start"]).days
    extras = None
    if r := first("get_cost_table"):
        items = {i["key"]: i for i in r["result"].get("items", [])}
        parts = [items.get(f"{trip['city'].lower()}_{k}") for k in ("stay_per_night", "food_per_day", "local_transport_per_day")]
        if all(parts):
            stay, food, local = parts
            extras = tuple(stay[k] * nights + (food[k] + local[k]) * (nights + 1) for k in ("low", "high"))
            note(r, f"Stay + food + local transport for {nights} night{'s' if nights != 1 else ''} / {nights + 1} days: {_rs(extras[0])} - {_rs(extras[1])}")
        else:
            note(r, f"No cost estimates for {trip['city']} yet")
    trip_cost = tuple(map(sum, zip(flights or (0, 0), extras or (0, 0)))) if (flights or extras) else None

    # --- money ---
    bal, summary, sips = first("get_balance"), first("get_spending_summary"), first("get_sips")
    if bal:
        note(bal, f"Balance {_rs(bal['result']['balance'])} (typed by user)")
    if summary:
        s = summary["result"]
        note(summary, f"Avg spend {_rs(s['monthly_avg_spend'])}/mo; fixed commitments {_rs(s['monthly_commitments'])}/mo")
    if sips:
        note(sips, f"SIPs {_rs(sips['result']['monthly_total'])}/mo ({len(sips['result']['sips'])} funds)")

    if not (bal and summary):
        tradeoffs += deadline_tradeoffs
        if free is None:
            return out("insufficient_data", "I can't see your calendar or your money yet. Plug in a source.", trip_cost=trip_cost)
        if free:
            return out("yes", "Your weekend is free. Looks fine. (Money not checked.)", trip_cost=trip_cost)
        return out("yes_with_conditions", "Only if you clear your calendar. (Money not checked.)", trip_cost=trip_cost)
    if trip_cost is None:
        tradeoffs += deadline_tradeoffs
        return out("insufficient_data", "I can't price this trip yet: plug in Travel or add cost estimates.")

    balance, commitments = bal["result"]["balance"], summary["result"]["monthly_commitments"]
    remaining = (balance - commitments - trip_cost[1], balance - commitments - trip_cost[0])
    gap = -remaining[0]
    money = []
    if gap <= 0:
        verdict, headline = "yes", f"Yes. Even the pricier version leaves {_rs(remaining[0])} above your safety floor."
    else:
        cuts, freed = [], 0
        for cat, amt in sorted(((c, a) for c, a in summary["result"]["monthly_avg_by_category"].items() if c in CUTTABLE), key=lambda x: -x[1]):
            if freed >= gap:
                break
            cuts.append((cat, amt))
            freed += amt
        money = [f"{CUTTABLE[c][0].upper()}{CUTTABLE[c][1:]} this month: frees ~{_rs(a)}" for c, a in cuts]
        if freed >= gap:
            verdict = "yes_with_conditions"
            headline = f"Only if you {_join_actions([CUTTABLE[c] for c, _ in cuts])} this month. Otherwise {trip['city']} eats your safety buffer."
        else:
            verdict = "no"
            headline = f"Not this month. Cutting every fun expense frees {_rs(freed)}, still {_rs(gap - freed)} short."
    if flights:
        money.append(f"Book the {o[0]['depart']} {o[0]['airline']} out and {b[0]['depart']} {b[0]['airline']} back, "
                     f"plus a budget stay: keeps it near {_rs(trip_cost[0])}")
    if sips:
        money.append(f"Your SIPs ({_rs(sips['result']['monthly_total'])}/mo) stay untouched")
    tradeoffs[:0] = money
    tradeoffs += deadline_tradeoffs
    if free is False and verdict == "yes":
        verdict, headline = "yes_with_conditions", "The money works, but your calendar isn't clear."
    return out(verdict, headline, balance, trip_cost, commitments, remaining)
