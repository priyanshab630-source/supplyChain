# Supply Chain Multi-Agent System

A LangGraph-orchestrated multi-agent system for gas tank supply-chain
management: inventory risk, consumption forecasting, supplier
reliability, a Neo4j knowledge graph, tank malfunction handling,
supplier allocation, shipment delay handling, an event simulator, and
a research evaluation suite.

## Repo layout

```
.
├── backend/       FastAPI service (HTTP + chat persistence) — backend/README.md
├── frontend/      React chat UI — frontend/README.md
├── PROJECT/       The actual multi-agent system — PROJECT/README.md
└── data/          Source CSVs seeded into the database
```

Each folder above, and every subfolder inside `PROJECT/`, has its own
`README.md` explaining what's in it and why. This file is only the
setup/run guide.

---

## Roadmap: what P0–P8 mean

You'll see these labels in commit messages, code comments, and design
docs across this repo. They track the business-requirement build-out,
in priority order — P0 first, P8 last, each one generally depending on
the ones before it being in place.

| # | Feature | What it does | Status |
|---|---|---|---|
| **P0** | Real business-context data | Switchover pairings, supplier contract shares, and the baseline SOP an operator follows today, sourced from Intel | **Blocked on Intel** — dummy data in use everywhere until this lands |
| **P1** | Knowledge-graph switchover topology | `BACKS_UP` relationships in Neo4j so the KG agent can answer "what covers Tank X if it fails", plus an ablation harness comparing the agent with vs. without this grounding | **Built** (on dummy P0 data) |
| **P2** | Tank malfunction handling | Detects a reported failure, finds the backup tank via P1's `BACKS_UP` relationship, activates it, and applies a consumption surge | **Built** |
| **P3** | Supplier schedule allocation | Splits demand for a gas across its contracted suppliers proportional to `contract_share`, redistributing if one supplier is unavailable | **Built** (on dummy P0 contract shares) |
| **P4** | Shipment delay handling | Given a delayed shipment, finds affected tanks, checks surge-aware urgency, and decides pull-in / push-out / escalate | **Built** |
| **P5** | Dynamic event simulator | A CLI/script that injects an event (malfunction, shipment delay, ...) and runs the full pipeline in reaction, the way a real alert feed would | **Not yet built** — the command in step 6 below is a placeholder for this |
| **P6** | Tank roles actually used in decisions | A tank's `ONLINE`/`STANDBY`/`MALFUNCTION` status and surge multiplier feed into risk and recommendation output, not just sit in a table | **Built**, via P2's surge hook (`tools/tank_status_tools.py`) — `RiskAgent`/`RecommendationAgent` inherit it automatically since they read already-adjusted inventory/forecast data |
| **P7** | Replace dummy switchover/contract data | Swap the placeholder pairings and equal contract shares for Intel's real numbers | **Waiting on Intel** — this is a data change only, no code changes needed once P0 lands |
| **P8** | Research evaluation | Expand the P1 ablation harness from a handful of scenarios to a real evaluation set, with proper groundedness/faithfulness metrics | **Partially built** — the harness exists (`PROJECT/graph/kg_ablation.py`), scenario count and metric rigor still need expanding |

The honest state of this repo at any point is: whatever's marked
**Built** above works against dummy P0 data and is real, working code.
Nothing downstream of P0 needs to change when real data arrives — only
the data-generation step itself does.

---

## Prerequisites

| Requirement | Version | Why |
|---|---|---|
| Python | 3.10+ | Backend + `PROJECT/` |
| [uv](https://docs.astral.sh/uv/) | latest | Python dependency management — faster and simpler than pip+venv |
| Node.js | 18+ | Frontend (Vite + React) |
| A database | Postgres (recommended) or SQLite (default fallback) | Domain data + chat history + checkpoints |
| Neo4j | Any recent version, local or Aura | Knowledge graph agent |
| Groq API key | — | Every LLM call in this system uses Groq |
| LangSmith API key | — | Optional, but required for tracing (see `PROJECT/observability/README.md`) |

**Installing uv**, if you don't have it yet:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# or, if you'd rather not run an install script, via pip itself:
pip install uv
```

---

## 1. Environment variables

Create `PROJECT/.env` (and copy the relevant ones into `backend/`'s
environment too, if you run it separately):

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/supply_chain
# or, for local dev with no Postgres: DATABASE_URL=sqlite:///./supply_chain.db
DATA_DATABASE_URL=${DATABASE_URL}        # can point elsewhere if you split domain data from chat history

# LangGraph checkpointing (only needed if it must differ from DATABASE_URL's format)
# LANGGRAPH_DB_URL=postgresql://user:password@localhost:5432/supply_chain

# Neo4j
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Groq
GROQ_API_KEY=your_groq_key

# LangSmith (optional but recommended)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=supply-chain-multi-agent
```

**Never commit `.env`.** Confirm it's in `.gitignore` before your first
commit, not after.

---

## 2. Install dependencies

```bash
# Python (from repo root) - uv creates and manages the venv for you
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

uv pip install -r backend/requirements.txt
uv pip install -r PROJECT/requirements.txt

# LangGraph checkpointing backend (pick ONE, matching your DATABASE_URL)
uv pip install langgraph-checkpoint-sqlite                                  # if sqlite
uv pip install langgraph-checkpoint-postgres psycopg[binary] psycopg-pool   # if postgresql

# LangSmith
uv pip install langsmith

# Frontend (npm unchanged - uv is Python-only)
cd frontend
npm install
cd ..
```

`uv venv` creates `.venv` in the repo root by default — if you already
have a `.venv` folder from a previous `python -m venv` setup, either
delete it first or point uv at a different path with `uv venv <name>`.

`uv pip install` is a drop-in replacement for `pip install` — same
flags, same `requirements.txt` files, just resolves and installs
significantly faster. Nothing else about the dependency list changes.

---

## 3. Seed the database (first run only)

```bash
python -m PROJECT.data_loader.seed_from_csv
python -m PROJECT.data_loader.add_switchover_and_contract_data
python -m PROJECT.data_loader.init_tank_status
python -m PROJECT.data_loader.init_shipment_status
python -m PROJECT.scripts.seed_backs_up_relationships
```

Re-run `seed_from_csv.py` any time you replace a CSV in `data/`, then
hit `POST /api/admin/refresh-data` (or restart) so the running app
picks up the change.

---

## 4. Run it

```bash
# Terminal 1 — backend
uvicorn backend.main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open the frontend's dev URL (Vite will print it, typically
`http://localhost:5173`).

---

## 5. Verify everything actually works

Don't just trust that it started — run through `RUN_CHECKLIST.md`
(provided earlier in this build) top to bottom. It's ordered
cheapest-and-fastest checks first specifically so a broken import or
bad env var gets caught in seconds, not after you've already started
the server and asked a question.

---

## 6. Optional: try the pieces beyond basic chat

```bash
# Simulate an event and watch the pipeline react automatically
python -m PROJECT.simulator.event_simulator tank-malfunction "Tank 1"

# Run the research evaluation suite
python -m PROJECT.eval.runner --repeat 3 --max-scenarios 10
```

Both write real (reversible) data changes — see their own READMEs'
warnings before running against a database anyone else is using.

**Note on current state:** these two commands correspond to P5 and the
expanded P8, both still in progress (see the roadmap table above). If
they're not in your checkout yet, the closest available equivalents
today are asking the chat directly (e.g. *"Tank 1 has malfunctioned"*
exercises the same P2 path a P5 simulator event would trigger) and
`python -m PROJECT.graph.kg_ablation` for the P1-level ablation harness
that P8 will expand on.

---

## ⚠️ Running this on a work/office laptop — read before you start

This system runs a local database, a local (or cloud) Neo4j instance,
calls an external LLM API (Groq) with your data, and optionally sends
trace data to a third-party service (LangSmith). On a company-managed
machine, several things can go wrong that have nothing to do with
your code:

- **Data policy / compliance.** If the seeded data represents real
  company inventory, supplier, or operational information, check with
  your IT/security team before sending any of it to Groq or LangSmith
  — both are external third-party services. Don't assume "it's just a
  demo" is a sufficient answer if the CSVs contain real data.
- **Corporate proxy/firewall.** Groq's API, Neo4j Aura (if you're not
  self-hosting), LangSmith, and even `npm`/`uv`'s package registries
  may be blocked or require a proxy configuration you don't control.
  If installs or API calls hang/timeout with no clear error, this is
  the first thing to check with IT — not a code bug.
- **Antivirus/EDR false positives.** Corporate endpoint protection
  sometimes flags newly-installed Python virtual environments or
  native-compiled packages (`psycopg`, database drivers) as
  suspicious. If `uv pip install` succeeds but the package "disappears"
  or imports fail mysteriously, check your AV/EDR quarantine log
  before assuming it's a code issue.
- **Admin rights.** Installing Python, Node.js, Postgres, or Neo4j for
  the first time may require local admin privileges you don't have on
  a managed device. Confirm what's already installed
  (`python --version`, `node --version`, `uv --version`) before
  assuming you need to install anything.
- **Port conflicts.** VPN clients, other corporate software, or a
  previously-installed Postgres instance may already occupy `8000`
  (backend), `5173` (frontend), `5432` (Postgres), or `7687` (Neo4j).
  Check with `netstat`/`lsof` before assuming the app itself is
  broken if it fails to bind.
- **VPN routing.** If your laptop is usually on a corporate VPN,
  `localhost`/`127.0.0.1` traffic is normally unaffected, but split-
  tunnel configurations occasionally interfere with local service
  discovery. Worth ruling out if `localhost:8000` is unreachable from
  the frontend despite the backend clearly running.
- **Sleep/hibernate.** A managed laptop's power policy may suspend the
  machine (and any local Postgres/Neo4j services) more aggressively
  than a personal one. If a long-running local database
  "disappears," check whether the machine slept rather than assuming
  data corruption.
- **Managed Python installs.** Some corporate images lock down or
  redirect the system Python. Always use the virtual environment from
  step 2 (`.venv`, created by `uv venv`) rather than installing
  packages globally — this also avoids needing admin rights for most
  of the Python side.

None of the above are bugs in this codebase — they're environment
issues specific to running local infrastructure and calling external
APIs from a managed device. Rule them out early rather than debugging
application code for a problem that's actually a network policy or
antivirus quarantine.
