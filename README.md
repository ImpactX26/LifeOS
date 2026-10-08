# LifeOS

**Your everyday AI that decides with you, and shows its evidence.**

LifeOS answers questions like *"Can I afford a Goa trip next weekend?"* using your real constraints: calendar, deadlines, spending, and commitments. Each source plugs in through MCP, and you control which sources it may read. Permissions are enforced in code, the money math is deterministic Python, and every answer comes with a data receipt showing what was read, from where, and how fresh it was.

- **Plan / who does what / save-the-demo:** [docs/PLAN.md](docs/PLAN.md)
- **Locked spec:** [docs/TEAM_BRIEF.md](docs/TEAM_BRIEF.md)
- **Engine ↔ UI contract:** [contracts/](contracts/)
- **Demo persona data (Manu, synthetic):** [data/](data/)

## Run (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Put your keys in `.env`. **Never commit `.env`**; see PLAN §9.

**Bank statements:** put raw CSVs in `data/raw/` (gitignored), then mask before use. Only date, category, debit and credit are kept:

```bash
python backend/statement_import.py data/raw/manu_statement_raw.csv data/manu_statement.masked.csv
pytest -q
```

**Frontend** (runs on mock data from `contracts/` until the backend's `POST /ask` exists):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 → **Ask** → plug in **Finance** → **Ask** again → the verdict flips.

**Full stack** (three terminals, all from the repo root with `.venv` active):

```bash
python run_servers.py
python backend\main.py
cd frontend; npm run dev
```

- **`run_servers.py`** starts the MCP servers: calendar :8101 · gmail :8102 · finance :8103 · travel :8104, each at `http://127.0.0.1:<port>/mcp`.
- **`backend\main.py`** is the API on :8000: `POST /ask`, `GET /servers`, `POST /servers/{name}/plug|unplug`.
- **The frontend** runs at http://localhost:5173. The pill shows `live · mcp servers` when it's connected to the API, and `api offline · mock data` when it has fallen back to the mock data.

Calendar and Gmail use seeded data until someone signs in to the Manu demo account (see [docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md)). To force seeded data, set `$env:LIFEOS_OFFLINE=1` before `run_servers.py`; this is the save-the-demo switch. Run the tests with `pytest -q`.

## Team

| Role | Who | Owns |
|---|---|---|
| A | Sai Siddarth | Frontend and design |
| B | Sai Gowrav | MCP servers, registry, FastAPI |
| C | Samarth Anil | Gemini loop, engine, Guardian |
| D | Pramegha M | Data, API integration, tests, pitch |
