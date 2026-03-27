import asyncio
import json

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from mcp_servers.server import (
    flag_nutritional_gaps,
    get_client_daily_summary,
    get_client_info,
    get_weekly_summary,
    list_clients_missing_logs,
    list_nutritionist_clients,
    lookup_food_nutrition,
    query_client_logs,
    search_clients_by_name,
    update_client_targets,
)
from prompts.query_prompt import build_query_system_prompt
from services.whatsapp import send_whatsapp_message
from utils.formatting import format_query_reply
from utils.memory import agent_memory


async def run_query_agent(nutritionist_obj, message_body: str):
    """Handles nutritionist questions autonomously via ReAct agent pipeline."""
    print(f"[Query Agent] Starting autonomous ReAct pipeline for {nutritionist_obj.name}")

    try:
        from langchain_groq import ChatGroq

        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, max_retries=1)
    except Exception as e:
        print("[Query Agent] Groq error:", e)
        send_whatsapp_message(nutritionist_obj.phone_number, "Sorry, Groq API is not ready right now.")
        return

    @tool
    def get_my_clients() -> str:
        """Fetch all clients assigned to this nutritionist, with IDs and names."""
        res = list_nutritionist_clients(nutritionist_obj.id)
        return json.dumps(res) if res else "No clients found."

    @tool
    def find_client_by_name(name_query: str) -> str:
        """Find likely clients by partial name for this nutritionist (use for fuzzy matches or spelling mistakes)."""
        res = search_clients_by_name(nutritionist_obj.id, name_query)
        return json.dumps(res) if res else "No matching clients found."

    @tool
    def get_client_weekly_progress(client_id: int) -> str:
        """Get a client's past 7-day average calories/protein and compliance percentages."""
        return json.dumps(get_weekly_summary(client_id))

    @tool
    def get_client_nutritional_gaps(client_id: int) -> str:
        """Identify days where a client significantly missed calorie target (too high or too low)."""
        res = flag_nutritional_gaps(client_id)
        return json.dumps(res) if res else "No gaps found."

    @tool
    def get_client_logs(client_id: int, days: int = 7) -> str:
        """Get a client's recent logs for the past N days."""
        res = query_client_logs(client_id, days)
        return json.dumps(res) if res else "No logs found."

    @tool
    def get_client_day_summary(client_id: int, date: str) -> str:
        """Get one-day totals for a client on a specific date (YYYY-MM-DD)."""
        return json.dumps(get_client_daily_summary(client_id, date))

    @tool
    def get_clients_missing_logs(days_without_logs: int = 3) -> str:
        """List this nutritionist's clients who have not logged for N days."""
        res = list_clients_missing_logs(nutritionist_obj.id, days_without_logs)
        return json.dumps(res) if res else "No clients are currently missing logs."

    @tool
    def get_client_profile(client_id: int) -> str:
        """Get a client's profile and targets (calories, protein, carbs, fat)."""
        return json.dumps(get_client_info(client_id))

    @tool
    def get_food_nutrition(query: str) -> str:
        """Lookup calories and macros for a food item. Pass product name only, e.g. 'chapati'."""
        return json.dumps(lookup_food_nutrition(query))

    @tool
    def set_client_targets(client_id: int, target_calories: int, target_protein_g: int) -> str:
        """Update a client's daily calorie and protein targets."""
        return json.dumps(update_client_targets(client_id, target_calories, target_protein_g))

    tools = [
        get_my_clients,
        find_client_by_name,
        get_client_weekly_progress,
        get_client_nutritional_gaps,
        get_client_logs,
        get_client_day_summary,
        get_clients_missing_logs,
        get_client_profile,
        get_food_nutrition,
        set_client_targets,
    ]

    system_prompt = build_query_system_prompt(nutritionist_name=nutritionist_obj.name)

    agent_executor = create_react_agent(model=llm, tools=tools, prompt=system_prompt, checkpointer=agent_memory)

    print("[Query Agent] Kickstarting agent tool execution loop with memory...")
    inputs = {"messages": [("user", message_body)]}
    config = {"configurable": {"thread_id": nutritionist_obj.phone_number}}

    try:
        response = await asyncio.wait_for(
            agent_executor.ainvoke(
                inputs,
                config={
                    **config,
                    "recursion_limit": 14,
                },
            ),
            timeout=45,
        )
        model_reply = response["messages"][-1].content
    except asyncio.TimeoutError:
        print("[Query Agent] Agent timeout after 45s; sending safe fallback.")
        model_reply = "I could not complete the analysis in time. Please retry with a shorter request."
    except Exception as e:
        print("[Query Agent] Agent invocation failed:", e)
        model_reply = "I hit a temporary issue while checking that. Please try again in a moment."

    final_reply_text = format_query_reply(str(model_reply), nutritionist_obj.name)
    print(f"[Query Agent] Execution complete. Final agent thought: {final_reply_text}")

    send_whatsapp_message(nutritionist_obj.phone_number, final_reply_text)
    return "done"
