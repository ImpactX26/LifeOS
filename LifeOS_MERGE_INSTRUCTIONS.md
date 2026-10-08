# LifeOS: Merge Instructions for Team Research Files

**Team:** MC-PleaseWork | **Event:** MCP24 Hackathon (MCP track, 24 hours) | **Project:** LifeOS

Each of us researched separately and has our own `.md` file. This file tells an AI how to **merge all of them into ONE combined `LifeOS_TEAM_BRIEF.md`**, fill the gaps, and flag conflicts. Everything below the line "Instructions for the AI" is written for the AI.

---

## How to use this file (for humans)

**Option A (recommended): one person merges.**
1. One teammate collects everyone's `.md` files and this file.
2. Open a new AI chat. Attach or paste ALL files (each one labelled with the author's name, e.g. `--- FILE FROM: Sai ---`).
3. Paste the "Ready-to-paste prompt" at the bottom of this file.
4. Read the output's **Conflicts** and **Gaps** sections first, and decide each one as a team.
5. Save the result as `LifeOS_TEAM_BRIEF.md`, commit it to the repo, and everyone works from that one file.

**Option B: if files are too big for one chat.** Merge two files, then merge the result with the next file, and so on. Always paste this instructions file again at each step.

**Do not merge by pasting files one after another.** The AI must deduplicate, resolve conflicts, and fill gaps.

---

# Instructions for the AI

You are a senior engineer and technical editor. You will receive several research `.md` files written by different teammates about the same hackathon project. Produce **one merged, consistent brief**.

## 1. Merge rules

1. **Preserve every unique fact.** If only one file mentions something (a tool, a library, a risk, a judge question), keep it.
2. **Deduplicate.** If several files say the same thing, keep the clearest version once. Do not repeat sections.
3. **Respect locked decisions.** The "Locked decisions" section below overrides any file that disagrees. If a teammate's file disagrees with a locked decision, do NOT silently overwrite either side: list it under **Proposed changes** with the teammate's reasoning, and keep the locked decision in the main text.
4. **Flag conflicts, never hide them.** Where two files disagree on something that is not locked (names of tools, numbers, library choices, time estimates), list both versions in a **Conflicts** table with the source of each and your recommendation. Do not pick silently.
5. **Tag the source** of non-obvious or unique content like this: `[from: Name]`. Content you add yourself is tagged `[AI-added]`.
6. **Never invent facts.** No made-up statistics, API limits, prices, library function names, quotes, or claims about the hackathon rules. If you are not sure, write `[UNVERIFIED: check official docs]`. API and SDK details change, so mark anything version-specific.
7. **Keep it actionable.** Prefer concrete schemas, tool names, file paths, and checklists over general explanations.
8. **Keep the neo-brutalist UI direction and the 5 differentiators intact** (see locked decisions).
9. **Do not include** personal phone numbers, API keys, or real financial data. All finance data in this project is fictional demo data.

## 2. Locked decisions (the source of truth)

**Project:** LifeOS. An AI that decides with the user and shows its evidence. Context sources are MCP servers. Tagline: "AI that decides with you, not for you."

**Problem statement:** Everyday AI assistants give advice without seeing a person's real constraints (schedule, deadlines, commitments, spending habits), and when they do get access, users cannot see or control what data was used. How can we build one AI assistant that safely combines context from many sources, in a permissioned and verifiable way, to support both big plans (trips, purchases) and daily money and time decisions?

**Hero demo question:** "Can I afford a Goa trip next weekend?" (also: "Can I buy a table?")

**MCP servers (names are final):**
| Server | Tools |
|---|---|
| Calendar | `list_events(start,end)`, `find_free_slots(start,end,min_minutes)` |
| Tasks | `list_tasks()`, `get_deadlines(start,end)` |
| Finance | `get_balance()`, `set_balance(amount)`, `get_sips()`, `get_spending_summary(days)`, `get_cost_table()` |
| Travel | `search_flights(origin,dest,date)`, returns `source` (live / cached / seeded) and `as_of` |
| Price Check | `check_price(item)` |
| Location (optional) | `get_current_city()` |
| LifeOS (we also expose it) | `can_i_afford(item, dates)`, `explain_last_answer()` (built last) |

**Privacy decisions:** no bank access; the user types in their balance; spending comes from an imported bank-statement CSV and an editable cost table; location is optional, permissioned, and read only while the app is in use; health data is out of scope; we do NOT claim a "live digital twin".

**Five differentiators (must be in the demo):**
1. Visible reasoning (servers light up, evidence flows into a verdict card).
2. A plan with trade-offs, not a yes/no.
3. The answer flips: with only Calendar and Tasks it says "looks fine", then we hot-plug the Finance server live and the answer changes.
4. Data receipt per answer (sources read and not read) plus per-source permission switches.
5. Proactive nudges (flight price drop, deadline change).
Plus: prompt-injection defense (untrusted text is data), and LifeOS exposed as an MCP server.

**Architecture rules:**
- The orchestrator never hardcodes source names. It calls `tools/list` on every registered server, merges the catalogue, gives it to the LLM, and routes `tools/call` to the owning server.
- The LLM plans and explains. **Deterministic Python does the money math** (low and high ranges, confidence labels).
- Write tools always need user approval. Permissions are enforced in our code, not in the prompt.
- Flight data uses layers: live, then cached, then seeded. Always return `source` and `as_of`, and show them in the data receipt.
- Amadeus Self-Service flight API was shut down on 17 July 2026. Do not recommend it.

**Stack:** React + Vite + Tailwind + React Flow + Framer Motion; FastAPI; Python MCP SDK; Gemini API (function calling + structured JSON output); local-first demo; JSON/CSV fixtures.

**UI style:** neo-brutalist "terminal sticker": cream grid background, orange and lime accents, 3px black outlines, hard offset shadows, condensed uppercase headlines, monospace `// label` pills, terminal-window cards.

**Demo data:** fictional persona "Manu", 25, salary 50k/month, PG rent 10k including food, metro daily, club every Sunday, party on Friday twice a month, dinner/games with friends twice a month, badminton twice a week. Files: `manu_statement_raw.csv` (upload test) and `manu_statement_categorized.csv` (ground truth). Closing balance on 30 Sep 2026 is Rs. 21,842. Average monthly spend about Rs. 46,300 (fixed commitments about Rs. 15,600).

**Verdict JSON (contract between engine and UI):**
```json
{
  "question": "",
  "verdict": "yes | yes_with_conditions | no | insufficient_data",
  "headline": "",
  "numbers": {
    "balance": 0,
    "trip_cost": {"low": 0, "high": 0},
    "monthly_commitments": 0,
    "remaining": {"low": 0, "high": 0}
  },
  "evidence": [{"server": "", "tool": "", "finding": "", "as_of": "", "source": ""}],
  "tradeoffs": [""],
  "not_read": [""]
}
```

**Roles:** (A) frontend and design, (B) MCP servers and orchestrator, (C) reasoning, safety and math, (D) data, integration and pitch. Names to be filled in by the team.

**Timeline (24 hours):** hours 0-1 contracts and repo; 1-6 mock servers, orchestrator discovery, UI skeleton, first agent loop; 6-13 real servers, end-to-end hero question, animation, receipt; 13-18 permissions, trace panel, hot-plug flip, injection defense; 18-21 nudge, LifeOS-as-server, polish; **hour 21 feature freeze**; 21-24 rehearse, fix bugs only, backup video.

**Still open (do not decide these; list them as open questions):** judging criteria and weights; whether prior code is allowed; whether outside APIs are allowed; final-round submission format and demo time limit.

**Already submitted/created:** a 5-slide PDF submission deck (PDF only, max 5 slides) covering team details, problem statement, idea title, solution summary and impact, technical approach, technologies, feasibility, scalability, beneficiaries, and innovation.

## 3. Required structure of the merged file

Output ONE markdown file named `LifeOS_TEAM_BRIEF.md` with these sections in this order:

1. **Status and open questions** (at the very top: what is decided, what is still open, owner for each open item)
2. **Conflicts between files** (table: topic | version A [from: Name] | version B [from: Name] | recommendation)
3. **Proposed changes to locked decisions** (only if a teammate argued for one, with reasoning)
4. **Product and pitch** (idea, persona, problem statement, differentiators, what we are NOT building)
5. **MCP primer for the team** (short and accurate; mark SDK-specific details as `[UNVERIFIED]` if not checked)
6. **Architecture** (diagram in text, components, data flow, orchestrator rules)
7. **MCP servers and tool schemas** (name, inputs, outputs, example JSON for every tool)
8. **Reasoning engine** (agent loop, deterministic math, verdict JSON, prompt principles, failure handling)
9. **Finance logic** (CSV import, categorization, monthly averages, SIPs and commitments, cost table, how estimates and ranges are computed)
10. **Travel and price data** (live, cached and seeded layers, source and as_of rules)
11. **Security and privacy** (prompt injection, permissions, approvals, data receipt, secrets handling)
12. **Hot-plug and discovery** (implementation steps for the Finance flip)
13. **Frontend and design** (screens, components, animation, style tokens)
14. **Repo structure, conventions and git workflow**
15. **Roles and task board** (task, owner, definition of done, status checkboxes)
16. **24-hour schedule** (hour-by-hour with checkpoints)
17. **Demo script** (about 3 minutes, step by step) and **judge Q&A**
18. **Risks and mitigations**
19. **Final checklist before submission**
20. **Appendix: content unique to one teammate that did not fit elsewhere** (kept so nothing is lost)

## 4. Gap check (do this after merging)

For each item, say **covered / partly covered / missing**. For anything partly covered or missing, **add it yourself, tagged `[AI-added]`**, as a concrete and minimal proposal:

- Every tool has an input schema, an output example, and an error case.
- Orchestrator registry design (how servers are added at runtime for hot-plug).
- How the Gemini function-calling loop turns the merged tool list into function declarations.
- CSV parsing rules (columns, date format, blank debit/credit handling) and the categorization approach (rules first, LLM fallback).
- How "monthly average spend" and "monthly commitments" are computed, with a worked example using the Manu data.
- Affordability formula and the exact meaning of `yes`, `yes_with_conditions`, `no`, `insufficient_data`.
- Permissions model (read-only / needs approval / off) and where it is enforced.
- Injection test fixture (one malicious calendar entry) and the expected behaviour.
- Error handling: timeouts, tool failure, invalid JSON from the LLM, retry once, cached replay.
- Observability: trace log fields (server, tool, args summary, latency, result size).
- Test plan: three hero questions with expected verdicts, and a cached replay mode.
- Environment setup steps (Python version, packages, `.env`, MCP Inspector).
- Known pitfalls (never `print()` to stdout in a stdio server, same Python interpreter path, CORS between React and FastAPI, geolocation needs HTTPS or localhost).

## 5. Output rules

- Output only the final merged markdown file, then a short **Merge report** after it containing: (a) which files were merged, (b) number of conflicts found, (c) number of gaps filled, (d) the top 5 things the team must decide.
- Use clear headings, tables for schemas, and code blocks for JSON and commands.
- Keep wording direct and practical. No motivational language.
- If the input is too long to merge in one pass, say so, merge in parts, and tell the user how to continue.

---

## Ready-to-paste prompt (for humans)

```
I'm attaching several .md files written by my teammates about our hackathon project (LifeOS), plus a file called LifeOS_MERGE_INSTRUCTIONS.md. Follow LifeOS_MERGE_INSTRUCTIONS.md exactly. Merge ALL the files into one LifeOS_TEAM_BRIEF.md using the required structure, flag every conflict in a table instead of choosing silently, keep the locked decisions as the source of truth, never invent facts, tag content you add yourself as [AI-added], and run the gap check at the end. Give me the merged file first and then the merge report.

The files are labelled below with each author's name.
```
