"""LifeOS API on 127.0.0.1:8000. Needs the MCP servers running (run_servers.py).

    .venv\\Scripts\\python backend\\main.py

POST /ask {"question": "..."}          -> {"verdict", "explanation", "trace", "planner", "model", "offline"}
GET  /servers                          -> which servers exist and which are plugged in
POST /servers/{name}/plug | /unplug    -> the hot-plug
POST /statement {"csv": "..."}         -> upload a bank statement: masked here, in memory, then handed to Finance
GET  /balance                          -> the balance from the uploaded statement (needs Finance plugged in)

/ask: Gemini decides which tools to read (rules planner if no model answers); Guardian checks every call;
the canonical reads the money rule needs are filled in if the model skipped them; engine.py decides;
Gemini explains. The verdict numbers only ever come from the engine.
"""
import asyncio
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import agent  # noqa: E402  (reads GEMINI_* from .env)
import engine  # noqa: E402
import guardian  # noqa: E402
import planner  # noqa: E402
import statement_import  # noqa: E402
from registry import SERVERS, Registry  # noqa: E402

TODAY = date.fromisoformat(os.getenv("LIFEOS_TODAY") or date.today().isoformat())  # frozen demo clock (PLAN P2)
GEMINI = agent.make_generate()  # None without GEMINI_API_KEY -> rules planner only

app = FastAPI(title="LifeOS")
registry = Registry(plugged=("calendar", "gmail", "travel", "price"))  # ponytail: one shared registry = one user (demo)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=300)


class Statement(BaseModel):
    csv: str = Field(min_length=10, max_length=2_000_000)


async def _finance(tool, args=None):
    """User actions on the Finance server. Never reachable from the model's tool loop."""
    if "finance" not in registry.plugged:
        raise HTTPException(409, "Plug in Finance first")
    r = await registry.call(f"finance__{tool}", args)
    if not r["ok"]:
        raise HTTPException(502, r["error"])
    return r["result"]


@app.get("/balance")
async def get_balance():
    return await _finance("get_balance")


@app.post("/statement")
async def upload_statement(body: Statement):
    """You uploading the file IS the approval Guardian requires for Finance's load_statement write tool.
    The raw file is masked in memory and never stored; Finance only ever receives date/category/debit/credit/balance."""
    try:
        masked, receipt = statement_import.mask_text(body.csv)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    return {"receipt": receipt, **await _finance("load_statement", {"statement": masked})}


@app.get("/servers")
def servers():
    return {"servers": [{"name": n, "plugged": n in registry.plugged} for n in SERVERS]}


def _known(name):
    if name not in SERVERS:
        raise HTTPException(404, f"unknown server '{name}'")


@app.post("/servers/{name}/plug")
def plug(name: str):
    _known(name)
    registry.plug(name)
    return servers()


@app.post("/servers/{name}/unplug")
def unplug(name: str):
    _known(name)
    registry.unplug(name)
    return servers()


def _key(name, args):
    return f"{name} {json.dumps(args, sort_keys=True)}"


@app.post("/ask")
async def ask(body: Question):
    catalogue = await registry.discover()
    tools = catalogue["tools"]

    def check(name):
        return guardian.check(name, tools)

    # 1. Understand: Gemini turns the question into an intent; code validates it. Rules parser if no model answers.
    chain, model, intent, planner_used = agent.models(), None, None, "rules"
    if GEMINI:
        try:
            model, raw = await agent.understand(body.question, TODAY, GEMINI, chain)
            chain, intent, planner_used = [model], planner.validate(raw, TODAY), "gemini"
        except Exception as e:
            planner_used = f"rules (Gemini unavailable: {str(e)[:120]})"
    intent = intent or planner.parse(body.question, TODAY)
    canonical = planner.plan(intent, tools, TODAY)
    needed = {_key(n, a) for n, a in canonical}
    other = intent["kind"] == "other"

    def enough(executed):
        return not other and needed <= {_key(f"{r['server']}__{r['tool']}", r["args"]) for r in executed if r["ok"]}

    # 2. Gather: the model chooses what to read; Guardian checks every call it asks for.
    executed, trace, answer = [], [], None
    if model and tools:  # no point asking a model to plan with zero tools
        try:
            _, executed, trace, answer = await agent.gather(
                body.question, planner.facts(intent, TODAY), tools, registry.call, check, GEMINI, chain, enough,
                system=agent.ANSWER if other else agent.SYSTEM)
        except Exception as e:
            planner_used = f"rules (Gemini unavailable: {str(e)[:120]})"

    # The numbers only use the canonical reads; whatever the model skipped or asked for differently is filled in here.
    done = {_key(f"{r['server']}__{r['tool']}", r["args"]): r for r in executed if r["ok"]}
    missing = [(n, a) for n, a in canonical if _key(n, a) not in done and check(n)[0] == "allowed"]
    topped_up = await asyncio.gather(*(registry.call(n, a) for n, a in missing))
    trace += [agent.entry(r, "rules") for r in topped_up]
    done |= {_key(n, a): r for (n, a), r in zip(missing, topped_up)}
    results = [done[_key(n, a)] for n, a in canonical if _key(n, a) in done]
    # Plugged-in servers that didn't answer show up in the receipt as FAILED, not silently as "not read".
    results += [{"server": n, "tool": "tools/list", "args": {}, "ok": False, "ms": 0, "error": f"server offline ({why})"}
                for n, why in catalogue["offline"].items()]

    # 3. Decide (deterministic engine), 4. explain (model, words only).
    verdict = engine.decide(body.question, intent, results, list(SERVERS))
    explanation = None
    if other:
        verdict["headline"] = answer or ('I can answer trips, purchases, outings and savings goals. '
                                         'Try: "Can I buy a laptop this month?"')
    elif model:
        try:
            explanation = await agent.explain(verdict, GEMINI, model)
        except Exception:
            pass  # the verdict stands on its own; the explanation is a nice-to-have
    shown = {k: v.isoformat() if isinstance(v, date) else v for k, v in intent.items()}
    return {"verdict": verdict, "explanation": explanation, "trace": trace, "planner": planner_used,
            "model": model, "intent": shown, "offline": catalogue["offline"]}


if __name__ == "__main__":
    import uvicorn

    here = str(Path(__file__).resolve().parent)
    # reload=True: editing any backend file restarts the API, so a stale backend can't serve old code
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, app_dir=here, reload_dirs=[here])
