import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agents.model_config import get_agent_model
from mcp_servers.server import (
    get_client_daily_summary,
    get_weekly_summary,
    log_meal,
    lookup_food_nutrition,
    query_client_logs,
)
from prompts.intake_prompt import build_intake_system_prompt
from services.whatsapp import send_whatsapp_message
from utils.formatting import format_intake_reply
from utils.memory import agent_memory


async def run_intake_agent(client_obj, message_body: str):
    """Parses client messages, logs meals, and sends structured WhatsApp responses."""
    print(f"[Intake Agent] Starting autonomous ReAct pipeline for {client_obj.name}")

    current_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")

    try:
        from langchain_groq import ChatGroq

        llm = ChatGroq(model=get_agent_model("INTAKE_AGENT"), temperature=0, max_retries=1)
    except Exception as e:
        print("[Intake Agent] Groq error:", e)
        send_whatsapp_message(
            client_obj.phone_number,
            "Sorry, I am having trouble analyzing your message right now. Please try again shortly.",
        )
        return

    nutrition_cache: dict[str, dict] = {}
    meal_logged_in_run = False

    @tool
    def fetch_food_nutrition(query: str) -> str:
        """Fetch nutrition macros (calories, protein, carbs, fat). Pass only product name, e.g. 'eggs'."""
        normalized_query = (query or "").strip().lower()
        if normalized_query in nutrition_cache:
            return json.dumps(nutrition_cache[normalized_query])
        data = lookup_food_nutrition(query)
        nutrition_cache[normalized_query] = data
        return json.dumps(data)

    @tool
    def log_client_meal(parsed_data_json: str) -> str:
        """Log meal data to DB. Uses the original client raw message from this webhook request."""
        nonlocal meal_logged_in_run
        if meal_logged_in_run:
            return json.dumps(
                {
                    "success": True,
                    "skipped": True,
                    "reason": "Meal already logged in this run. Continue to final response.",
                }
            )
        meal_logged_in_run = True
        return json.dumps(log_meal(client_obj.id, message_body, parsed_data_json))

    @tool
    def query_recent_logs(days: int = 7) -> str:
        """Get this client's meal logs for the past N days."""
        res = query_client_logs(client_obj.id, days)
        return json.dumps(res) if res else "No recent logs found."

    @tool
    def get_progress_summary() -> str:
        """Get this client's past 7-day average calories/protein and compliance summary."""
        return json.dumps(get_weekly_summary(client_obj.id))

    @tool
    def get_day_summary(date: str) -> str:
        """Get this client's one-day totals for a specific date (YYYY-MM-DD)."""
        return json.dumps(get_client_daily_summary(client_obj.id, date))

    tools = [fetch_food_nutrition, log_client_meal, query_recent_logs, get_progress_summary, get_day_summary]

    base_prompt = build_intake_system_prompt(
        client_name=client_obj.name,
        current_date=current_date,
        target_calories=client_obj.target_calories,
        target_protein_g=client_obj.target_protein_g,
    )
    system_prompt = (
        f"{base_prompt}\n\n"
        "Hard limits for this turn:\n"
        "- Use at most 6 total tool calls.\n"
        "- Use at most 3 fetch_food_nutrition calls.\n"
        "- Call log_client_meal at most once.\n"
        "- After required tool calls, stop and provide the final formatted response immediately.\n"
    )

    agent_executor = create_react_agent(model=llm, tools=tools, prompt=system_prompt, checkpointer=agent_memory)

    print("[Intake Agent] Kickstarting agent tool execution loop with memory...")
    inputs = {"messages": [("user", f"Client Message: {message_body}")]}
    config = {"configurable": {"thread_id": client_obj.phone_number}}

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
        print("[Intake Agent] Agent timeout after 45s; sending safe fallback.")
        model_reply = (
            "Date: "
            f"{current_date}\n"
            f"Client: {client_obj.name}\n\n"
            "Logged Items:\n"
            "- Update received\n\n"
            "Today's Intake:\n"
            "- Calories: Not available yet\n"
            "- Protein: Not available yet\n\n"
            "Guidance:\n"
            "I received your update but analysis took too long. Please resend once in a shorter format."
        )
    except Exception as e:
        print("[Intake Agent] Agent invocation failed:", e)
        model_reply = "I saved what I could from your update. Please resend if you want a detailed breakdown."

    final_reply_text = format_intake_reply(
        str(model_reply),
        client_obj.name,
        current_date=current_date,
        message_body=message_body,
        target_calories=client_obj.target_calories,
        target_protein_g=client_obj.target_protein_g,
    )
    print(f"[Intake Agent] Execution complete. Final agent thought: {final_reply_text}")

    send_whatsapp_message(client_obj.phone_number, final_reply_text)
    return "done"
