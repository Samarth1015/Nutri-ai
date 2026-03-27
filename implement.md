# 🥗 NutriCoach AI — Implementation Plan

> **Product:** WhatsApp-native AI nutrition CRM for dietitians and nutritionists  
> **Stack:** LangGraph · LangChain · MCP · FastAPI · WhatsApp API · PostgreSQL · LangSmith  
> **Estimated Build Time:** 3–4 weeks (part-time) to MVP  
> **First Customer:** Your relative (nutritionist) — real feedback loop from day one

---

## 🗺️ System Architecture Overview

```
 CLIENTS
 ┌───────────────────┐   ┌──────────────────────┐   ┌────────────────────┐
 │  Client WhatsApp  │   │  Nutritionist WA/Web  │   │  Dashboard (Later) │
 └────────┬──────────┘   └──────────┬────────────┘   └────────┬───────────┘
          │                         │                          │
          └──────────────┬──────────┘                         │
                         ▼                                     │
 GATEWAY                                                       │
 ┌─────────────────────────────┐   ┌────────────────────────────┘
 │  WhatsApp API (Twilio/Meta) │──▶│  FastAPI Backend (webhook + router)
 └─────────────────────────────┘   └──────────────┬─────────────────────┘
                                                   │
 LANGGRAPH AGENTS                                  ▼
 ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
 │   Intake Agent  │   │   Query Agent   │   │   Report Agent  │
 │ parses client   │   │ nutritionist    │   │ weekly auto-    │
 │ meal messages   │   │ asks questions  │   │ generated PDFs  │
 └───────┬─────────┘   └────────┬────────┘   └────────┬────────┘
         │                      │                      │
 MCP TOOL SERVER ───────────────┴──────────────────────┘
 ┌──────────────────────────────────────────────────────────────┐
 │  log_meal · query_client · get_weekly_summary · flag_gaps    │
 └──────────────────────────────┬───────────────────────────────┘
                                │
 STORAGE                        ▼
 ┌────────────────────┐   ┌──────────────────┐   ┌─────────────────────┐
 │  PostgreSQL DB     │   │  LangGraph State │   │  Nutritionix/USDA   │
 │  per-client rows   │   │  session memory  │   │  nutrition lookup   │
 └────────────────────┘   └──────────────────┘   └─────────────────────┘

 OBSERVABILITY
 ┌──────────────────────────────────────────────────────────────┐
 │  LangSmith — full trace of every agent decision + token use  │
 └──────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Project Structure

```
nutricoach-ai/
│
├── main.py                        # FastAPI app entry point
├── .env                           # All API keys
├── requirements.txt
├── docker-compose.yml             # Postgres + app container
│
├── api/
│   ├── __init__.py
│   ├── webhook.py                 # WhatsApp webhook receiver
│   ├── router.py                  # Routes message to correct agent
│   └── schemas.py                 # Pydantic request/response models
│
├── agents/
│   ├── __init__.py
│   ├── intake_agent.py            # Parses client meal logs
│   ├── query_agent.py             # Handles nutritionist questions
│   └── report_agent.py            # Generates weekly summaries
│
├── graph/
│   ├── __init__.py
│   ├── state.py                   # Shared AgentState (TypedDict)
│   ├── graph_builder.py           # LangGraph StateGraph wiring
│   └── supervisor.py              # Decides which agent handles the msg
│
├── mcp_server/
│   ├── __init__.py
│   ├── server.py                  # MCP server exposing DB tools
│   └── tools/
│       ├── log_meal.py
│       ├── query_client.py
│       ├── get_weekly_summary.py
│       └── flag_nutritional_gaps.py
│
├── db/
│   ├── __init__.py
│   ├── models.py                  # SQLAlchemy models
│   ├── crud.py                    # DB operations
│   └── migrations/                # Alembic migrations
│
├── services/
│   ├── whatsapp.py                # Twilio/Meta send message wrapper
│   ├── nutrition.py               # Nutritionix / USDA API calls
│   └── scheduler.py               # APScheduler for weekly reports
│
├── prompts/
│   ├── intake_prompt.py
│   ├── query_prompt.py
│   └── report_prompt.py
│
├── utils/
│   ├── langsmith_config.py        # Tracing setup
│   ├── phone_utils.py             # Normalize phone numbers
│   └── pdf_generator.py           # WeasyPrint/ReportLab for report PDFs
│
└── tests/
    ├── test_intake_agent.py
    ├── test_query_agent.py
    └── test_mcp_tools.py
```

---

## 🔢 Phase-by-Phase Implementation

---

### ✅ Phase 1 — Project Setup & Environment (Day 1)

**Goal:** Skeleton running, API keys wired, LangSmith tracing live.

**Tasks:**
- [ ] Create virtual environment (`python -m venv venv`)
- [ ] Configure `.env` with all keys (see below)
- [ ] Initialize FastAPI app with a `/health` endpoint
- [ ] Set up PostgreSQL via Docker (`docker-compose up`)
- [ ] Verify LangSmith dashboard shows a traced LLM call

**Environment variables needed:**
```env
# LLM
OPENAI_API_KEY=

# WhatsApp
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/nutricoach

# Nutrition API
NUTRITIONIX_APP_ID=
NUTRITIONIX_API_KEY=

# LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=nutricoach-ai
LANGCHAIN_API_KEY=
```

**Packages to install:**
```
fastapi uvicorn
langchain langchain-openai langgraph langsmith
twilio
sqlalchemy alembic psycopg2-binary
httpx python-dotenv pydantic
apscheduler
reportlab
```

**Deliverable:** `GET /health` returns 200, LangSmith shows a trace ✅

---

### ✅ Phase 2 — Database Schema Design (Day 2)

**Goal:** Design the PostgreSQL schema that all agents read and write.

**File:** `db/models.py`

```python
# Key tables:

class Nutritionist(Base):
    id, name, phone_number (unique), whatsapp_number, created_at

class Client(Base):
    id, nutritionist_id (FK), name, phone_number (unique),
    target_calories, target_protein_g, target_carbs_g, target_fat_g,
    created_at

class MealLog(Base):
    id, client_id (FK), logged_at,
    raw_message,           # "had poha for breakfast and dal rice"
    parsed_meals (JSON),   # [{"food": "poha", "calories": 250, ...}]
    total_calories, total_protein_g, total_carbs_g, total_fat_g,
    workout_notes, weight_kg

class WeeklyReport(Base):
    id, client_id (FK), week_start, week_end,
    avg_calories, avg_protein, compliance_score,
    report_pdf_url, generated_at
```

**Key design decisions:**
- `phone_number` is the identity key — this is how we map WhatsApp senders to clients
- `parsed_meals` stored as JSON — flexible for different meal types
- One `MealLog` row per day per client

**Deliverable:** `alembic upgrade head` creates all tables ✅

---

### ✅ Phase 3 — WhatsApp Webhook + Message Router (Day 3)

**Goal:** Receive WhatsApp messages, identify the sender, route to the right agent.

**File:** `api/webhook.py`

```python
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    data = await request.form()
    sender_phone = data.get("From")          # "whatsapp:+919876543210"
    message_body = data.get("Body")

    # Identify: is this a client or a nutritionist?
    sender_type, sender = identify_sender(sender_phone)

    if sender_type == "client":
        await run_intake_agent(sender, message_body)
    elif sender_type == "nutritionist":
        await run_query_agent(sender, message_body)
```

**File:** `api/router.py` — `identify_sender()` logic

```python
def identify_sender(phone: str):
    normalized = normalize_phone(phone)       # strip "whatsapp:" prefix

    # Check nutritionists table first
    nutritionist = db.query(Nutritionist).filter_by(phone=normalized).first()
    if nutritionist:
        return "nutritionist", nutritionist

    # Then check clients table
    client = db.query(Client).filter_by(phone=normalized).first()
    if client:
        return "client", client

    return "unknown", None
```

**Deliverable:** Twilio sandbox configured, test message routed correctly in logs ✅

---

### ✅ Phase 4 — MCP Tool Server (Day 4–5)

**Goal:** Expose all DB operations as MCP tools so LangGraph agents can call them.

**File:** `mcp_server/server.py`

```python
from mcp.server import MCPServer

server = MCPServer("nutricoach-db-tools")

@server.tool("log_meal")
def log_meal(client_id: int, raw_message: str, parsed_data: dict) -> dict:
    """Log a client's meal entry to the database"""
    # Writes to MealLog table
    # Returns: { success, log_id, total_calories }

@server.tool("query_client_logs")
def query_client_logs(client_id: int, days: int = 7) -> list:
    """Get a client's meal logs for the past N days"""
    # Returns: list of MealLog rows

@server.tool("get_client_by_phone")
def get_client_by_phone(phone: str) -> dict:
    """Look up a client by their WhatsApp phone number"""
    # Returns: client details + targets

@server.tool("get_weekly_summary")
def get_weekly_summary(client_id: int) -> dict:
    """Calculate weekly averages and compliance score"""
    # Returns: avg_calories, avg_protein, compliance_%, flagged_days

@server.tool("flag_nutritional_gaps")
def flag_nutritional_gaps(client_id: int) -> list:
    """Identify days where targets were significantly missed"""
    # Returns: list of flagged dates with details

@server.tool("list_nutritionist_clients")
def list_nutritionist_clients(nutritionist_id: int) -> list:
    """Get all active clients for a nutritionist"""
    # Returns: list of client summaries
```

**Why MCP here?**
MCP makes your DB operations callable as first-class tools by LangGraph agents — this is the pattern companies use in production. It also means if you later add more tools (e.g. appointment booking), you just register them in the MCP server without touching the agent logic.

**Deliverable:** MCP server runs standalone, all 6 tools callable via test script ✅

---

### ✅ Phase 5 — LangGraph Shared State (Day 5)

**Goal:** Define the `AgentState` TypedDict used across all agents.

**File:** `graph/state.py`

```python
from typing import TypedDict, Optional, List, Annotated
import operator

class AgentState(TypedDict):
    # Incoming message context
    sender_phone: str
    sender_type: str                    # "client" or "nutritionist"
    raw_message: str
    sender_id: int                      # DB id of sender

    # Client context (populated after lookup)
    client_id: Optional[int]
    client_name: Optional[str]
    nutritionist_id: Optional[int]

    # Agent processing results
    parsed_meal_data: Optional[dict]    # Output of NLP parsing
    nutrition_data: Optional[dict]      # From Nutritionix API
    query_results: Optional[dict]       # DB query results
    report_data: Optional[dict]         # Weekly summary data

    # Response
    reply_message: Optional[str]        # WhatsApp reply to send
    action_taken: Optional[str]         # What the agent did (for logging)

    # LangGraph internals
    messages: Annotated[list, operator.add]
    current_step: str
```

---

### ✅ Phase 6 — Build the 3 Agents (Day 6–10)

---

#### 6A. Intake Agent — parses client meal messages

**File:** `agents/intake_agent.py`

**Responsibility:** When a client sends a message, parse it, look up nutrition data, log to DB, reply with a confirmation.

**LangGraph flow for this agent:**

```
START
  │
  ▼
lookup_client (MCP: get_client_by_phone)
  │
  ▼
parse_meal_nlp (LLM: extract structured meal data from raw text)
  │
  ▼
fetch_nutrition (Nutritionix API: get calories/macros per food item)
  │
  ▼
log_to_db (MCP: log_meal)
  │
  ▼
compose_reply (LLM: write a friendly WhatsApp confirmation)
  │
  ▼
send_whatsapp (Twilio API)
  │
  END
```

**Sample parse_meal_nlp prompt:**
```
You are a nutrition assistant. Extract all food and drink items from this message.
Message: "{raw_message}"

Return JSON:
{
  "meals": [{"item": "poha", "quantity": "1 plate", "meal_type": "breakfast"}],
  "workout": {"type": "walk", "duration_minutes": 30} or null,
  "weight_kg": 68.5 or null
}
Return ONLY valid JSON. No explanation.
```

**Sample client reply the agent sends back:**
```
✅ Logged for today!

🍽️ Meals: Poha, Dal rice
🔥 ~1,380 kcal
💪 Protein: 42g / 60g target

You're 280 kcal below your target — consider a light evening snack.
Keep it up! 🙌
```

---

#### 6B. Query Agent — handles nutritionist questions

**File:** `agents/query_agent.py`

**Responsibility:** The nutritionist sends a WhatsApp message asking about a client. The agent understands the intent, queries the DB via MCP, and replies with a useful answer.

**LangGraph flow:**

```
START
  │
  ▼
classify_intent (LLM: what is the nutritionist asking?)
  │
  ├── "client_status" → get_weekly_summary (MCP)
  ├── "compliance_check" → flag_nutritional_gaps (MCP)
  ├── "list_clients" → list_nutritionist_clients (MCP)
  └── "specific_day" → query_client_logs (MCP)
  │
  ▼
format_response (LLM: convert DB data into a clear WhatsApp message)
  │
  ▼
send_whatsapp
  │
  END
```

**Example queries the nutritionist can send:**
- *"How is Priya doing this week?"* → weekly summary
- *"Who hasn't logged in the last 3 days?"* → compliance check across all clients
- *"Show Rahul's logs from Monday"* → specific day lookup
- *"Which clients are consistently missing their protein target?"* → nutritional gap analysis

**classify_intent prompt:**
```
You are an assistant for a nutritionist managing multiple clients.
Nutritionist message: "{message}"
Client list: {client_names}

Classify the intent as one of:
- client_status (asking about a specific client's overall progress)
- compliance_check (asking who has/hasn't logged or is missing targets)
- specific_day (asking about a specific date's logs)
- list_clients (asking for a list of all clients)

Return JSON: { "intent": "...", "client_name": "..." or null, "date": "..." or null }
```

---

#### 6C. Report Agent — weekly auto-generated summaries

**File:** `agents/report_agent.py`

**Responsibility:** Runs every Sunday automatically. For each client, generates a detailed weekly PDF and sends it to the nutritionist on WhatsApp.

**LangGraph flow:**

```
START (triggered by APScheduler every Sunday 8am)
  │
  ▼
get_all_clients (MCP: list_nutritionist_clients)
  │
  ▼
[for each client]:
  │
  ├── get_weekly_summary (MCP)
  ├── flag_nutritional_gaps (MCP)
  ├── generate_report_text (LLM)
  ├── render_pdf (ReportLab/WeasyPrint)
  └── send_to_nutritionist (WhatsApp with PDF attachment)
  │
  END
```

**PDF report sections:**
1. Client overview (name, targets, compliance score %)
2. Day-by-day calorie & macro chart (text-based table for MVP)
3. Key observations (LLM generated — e.g. "Priya consistently skips dinner on weekdays")
4. Recommendations for next week

**Deliverable:** All 3 agents tested with mock state data ✅

---

### ✅ Phase 7 — Wire the LangGraph Supervisor (Day 11)

**Goal:** Connect all agents into a `StateGraph` with the supervisor routing messages.

**File:** `graph/supervisor.py`

```python
def supervisor_node(state: AgentState) -> AgentState:
    """
    Decides which agent handles this message.
    - Client message → intake_agent
    - Nutritionist message → query_agent
    - Scheduled trigger → report_agent
    """
    if state["sender_type"] == "client":
        return {**state, "current_step": "intake"}
    elif state["sender_type"] == "nutritionist":
        return {**state, "current_step": "query"}
    else:
        return {**state, "current_step": "end"}
```

**File:** `graph/graph_builder.py`

```python
from langgraph.graph import StateGraph, END

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor",     supervisor_node)
    graph.add_node("intake_agent",   intake_agent_node)
    graph.add_node("query_agent",    query_agent_node)
    graph.add_node("report_agent",   report_agent_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        lambda s: s["current_step"],
        {
            "intake":  "intake_agent",
            "query":   "query_agent",
            "report":  "report_agent",
            "end":     END,
        }
    )

    graph.add_edge("intake_agent",  END)
    graph.add_edge("query_agent",   END)
    graph.add_edge("report_agent",  END)

    return graph.compile()
```

**Deliverable:** Full pipeline — WhatsApp in → agent processes → WhatsApp reply out ✅

---

### ✅ Phase 8 — LangSmith Observability (Day 12)

**Goal:** Every agent decision fully traced and debuggable.

**File:** `utils/langsmith_config.py`

```python
import os
from langsmith import Client

def setup_tracing():
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "nutricoach-ai"

# Add custom metadata to traces
def tag_run(run_id: str, client_name: str, agent: str):
    ls_client = Client()
    ls_client.update_run(run_id, metadata={
        "client_name": client_name,
        "agent": agent
    })
```

**What to trace and check in LangSmith:**
- Token usage per agent (helps optimize prompts and cost)
- Latency per step (identify bottlenecks)
- Meal parsing accuracy (did the LLM correctly identify "poha" as a meal?)
- Agent decision path (supervisor → intake vs query)
- Full message history for debugging hallucinations

**Pro tip:** Screenshot your LangSmith trace view for the resume/portfolio — it visually proves production-grade thinking.

---

### ✅ Phase 9 — Testing & Hardening (Day 13–14)

**Test scenarios to cover:**

| Scenario | Expected behavior |
|---|---|
| Client sends meal in Hindi/mixed language | Agent parses correctly or asks for clarification |
| Client sends multiple meals in one message | All meals extracted and logged |
| Unknown phone number sends a message | Agent replies "You're not registered, contact your nutritionist" |
| Nutritionist asks about non-existent client | Agent replies gracefully with "I couldn't find a client named X" |
| Client logs workout only (no food) | Agent logs workout, doesn't require food data |
| Weekly report — client with zero logs | Report says "No logs recorded this week" |
| Nutritionix API is down | Fallback to manual macro estimation via LLM |

**File structure for tests:**
```
tests/
├── test_intake_agent.py    # Mock WhatsApp message → assert DB log created
├── test_query_agent.py     # Mock nutritionist question → assert correct reply
├── test_mcp_tools.py       # Each MCP tool tested in isolation
└── test_router.py          # Phone number → correct sender type
```

---

### ✅ Phase 10 — MVP Polish & Launch Prep (Day 15–18)

**Minimum for showing your relative:**

- [ ] Client registration flow — nutritionist adds a new client via WhatsApp command: *"Add client Priya +91XXXXXXXXXX calories:1600 protein:60g"*
- [ ] Onboarding message — when a new client texts for the first time, send a friendly welcome
- [ ] Error handling — every agent has a fallback reply if something breaks
- [ ] Rate limiting — prevent spam (max 10 messages per client per hour)
- [ ] `.env` → production secrets management (Railway env vars)
- [ ] Deploy to Railway or Render (FastAPI + PostgreSQL)

**Nice-to-haves for V2 (after getting first feedback):**
- Web dashboard for the nutritionist (React/Next.js)
- PDF report email delivery in addition to WhatsApp
- Multi-language support (Gujarati, Hindi)
- Photo meal logging — client sends a food photo, vision model estimates calories
- Stripe/Razorpay integration for subscription billing

---

## 💰 Monetization Plan

### Pricing (Indian market — adjust for global)

| Plan | Price/month | Client limit | Features |
|---|---|---|---|
| Starter | ₹999 | 10 clients | Logging + basic query |
| Pro | ₹2,499 | 50 clients | Logging + queries + weekly reports |
| Clinic | ₹5,999 | Unlimited | All features + multi-staff + custom branding |

### Go-to-Market Steps

1. **Month 1:** Build for your relative (free) — fix bugs with real usage
2. **Month 2:** He refers 2–3 nutritionist friends at ₹499/month (beta price)
3. **Month 3:** Post a demo video on LinkedIn showing before/after workflow
4. **Month 4+:** Join nutritionist Facebook groups, Instagram communities, cold DM

### Why nutritionists will pay
- Currently managing clients via WhatsApp + Google Sheets manually — 2–3 hours of admin/day
- WhatsApp is already their default tool — zero behavior change required
- ₹999/month is less than 1 client session fee — the ROI is obvious

---

## 🔑 Key Concepts You Will Learn

| Concept | Where You Use It |
|---|---|
| `StateGraph` with conditional edges | Supervisor routing to correct agent |
| Tool-calling agents | All 3 agents via MCP tools |
| MCP Server design | Exposing DB as agent-callable tools |
| Structured LLM output (`with_structured_output`) | Meal parsing, intent classification |
| LangSmith tracing + metadata tagging | Full observability |
| Webhook design (FastAPI) | WhatsApp message receiver |
| Scheduled agentic jobs (APScheduler) | Sunday report generation |
| LangGraph memory/checkpointing | Nutritionist conversation context |

---

## 📋 Resume Description (Copy-Paste Ready)

> **NutriCoach AI** | LangGraph · LangChain · MCP · FastAPI · WhatsApp API · LangSmith · PostgreSQL
>
> Built a production WhatsApp-native AI system for nutritionists to manage multi-client diet tracking at scale. Designed a 3-agent LangGraph pipeline (Intake Agent, Query Agent, Report Agent) orchestrated by a supervisor with conditional routing. Exposed all database operations as MCP tools (`log_meal`, `query_client`, `flag_nutritional_gaps`), allowing agents to interact with PostgreSQL via structured tool-calling. Clients log meals in natural language on WhatsApp; the agent parses macros via Nutritionix API, logs structured data, and replies with a real-time summary. Nutritionist can query any client's progress via WhatsApp natural language. Weekly PDF reports auto-generated every Sunday via APScheduler. Full observability via LangSmith with per-run metadata tagging.

---

## 📅 Timeline Summary

| Phase | Days | Deliverable |
|---|---|---|
| 1. Setup & Environment | 1 | FastAPI running, LangSmith tracing live |
| 2. Database Schema | 2 | All tables created via Alembic |
| 3. Webhook + Router | 3 | WhatsApp messages received and routed |
| 4. MCP Tool Server | 4–5 | All 6 DB tools callable by agents |
| 5. Shared State | 5 | `AgentState` TypedDict defined |
| 6. Build 3 Agents | 6–10 | All agents tested with mock data |
| 7. LangGraph Wiring | 11 | Full pipeline end-to-end |
| 8. LangSmith | 12 | Every agent decision traced |
| 9. Testing | 13–14 | All key scenarios covered |
| 10. MVP Polish | 15–18 | Ready to show your relative |