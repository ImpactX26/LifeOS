"""LifeOS API on 127.0.0.1:8000. Needs the MCP servers running (run_servers.py).

    .venv\\Scripts\\python backend\\main.py

POST /ask {"question": "..."}          -> {"verdict": <contracts/ JSON>, "trace": [...], "offline": {...}, "planner": "rules"}
GET  /servers                          -> which servers exist and which are plugged in
POST /servers/{name}/plug | /unplug    -> the hot-plug
"""
import asyncio
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import engine
import planner
from registry import SERVERS, Registry

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
TODAY = date.fromisoformat(os.getenv("LIFEOS_TODAY") or date.today().isoformat())  # frozen demo clock (PLAN P2)

app = FastAPI(title="LifeOS")
registry = Registry(plugged=("calendar", "gmail", "travel"))  # ponytail: one shared registry = one user (demo)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=300)


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


@app.post("/ask")
async def ask(body: Question):
    catalogue = await registry.discover()
    trip, calls = planner.plan(body.question, catalogue["tools"], TODAY)
    results = list(await asyncio.gather(*(registry.call(name, args) for name, args in calls)))
    trace = [{k: r[k] for k in ("server", "tool", "args", "ok", "ms")} | ({} if r["ok"] else {"error": r["error"]}) for r in results]
    return {
        "verdict": engine.decide(body.question, trip, results, list(SERVERS)),
        "trace": trace,
        "offline": catalogue["offline"],
        "planner": "rules",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
