import asyncio
from langgraph.graph import StateGraph, END
from graph.state import AgentState
from graph.supervisor import supervisor_node
from agents.intake_agent import run_intake_agent
from agents.query_agent import run_query_agent
from agents.report_agent import run_report_agent
from agents.general_agent import run_general_agent
from db.database import SessionLocal
from db.models import Client, Nutritionist

async def intake_agent_node(state: AgentState) -> dict:
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == state.get("sender_id")).first()
        if client:
            await run_intake_agent(client, state.get("raw_message", ""))
    finally:
        db.close()
    return {"current_step": "end"}

async def query_agent_node(state: AgentState) -> dict:
    db = SessionLocal()
    try:
        nutri = db.query(Nutritionist).filter(Nutritionist.id == state.get("sender_id")).first()
        if nutri:
            await run_query_agent(nutri, state.get("raw_message", ""))
    finally:
        db.close()
    return {"current_step": "end"}

async def general_agent_node(state: AgentState) -> dict:
    await run_general_agent(state.get("sender_phone", ""), state.get("raw_message", ""))
    return {"current_step": "end"}

async def report_agent_node(state: AgentState) -> dict:
    db = SessionLocal()
    try:
        nutri = db.query(Nutritionist).filter(Nutritionist.id == state.get("sender_id")).first()
        if nutri:
            await run_report_agent(nutri)
    finally:
        db.close()
    return {"current_step": "end"}

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor",     supervisor_node)
    graph.add_node("intake_agent",   intake_agent_node)
    graph.add_node("query_agent",    query_agent_node)
    graph.add_node("general_agent",  general_agent_node)
    graph.add_node("report_agent",   report_agent_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        lambda s: s.get("current_step", "end"),
        {
            "intake":  "intake_agent",
            "query":   "query_agent",
            "general": "general_agent",
            "report":  "report_agent",
            "end":     END,
        }
    )

    graph.add_edge("intake_agent",  END)
    graph.add_edge("query_agent",   END)
    graph.add_edge("general_agent", END)
    graph.add_edge("report_agent",  END)

    return graph.compile()
