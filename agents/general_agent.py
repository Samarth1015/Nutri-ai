import asyncio
import json

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agents.model_config import get_agent_model
from mcp_servers.server import lookup_food_nutrition
from services.whatsapp import send_whatsapp_message

GENERAL_SYSTEM_PROMPT = """
You are a helpful AI assistant for NutriCoach, a WhatsApp-native dietary CRM for nutritionists.
The user might be unregistered or asking a general nutrition question.

You can do two things:
1. Onboarding help: explain NutriCoach features and how to get registered.
2. Nutrition lookup: if user asks macros/calories for a food item, use `get_food_nutrition` and answer from tool output.

Response rules:
- Keep it concise (3-5 short sentences).
- If user is unregistered and asks account-specific data, guide them to ask their nutritionist to register the number.
- For nutrition lookup, keep it factual and include calories/protein/carbs/fat when available.
- Never output tool syntax or JSON in final response.
"""


async def run_general_agent(phone_number: str, message_body: str):
    """Handles messages from unknown numbers with onboarding + basic nutrition lookup."""
    print(f"[General Agent] Responding to unknown number {phone_number}")

    try:
        from langchain_groq import ChatGroq

        llm = ChatGroq(model=get_agent_model("GENERAL_AGENT"), temperature=0, max_retries=1)
    except Exception as e:
        print("[General Agent] Groq not configured correctly:", e)
        send_whatsapp_message(phone_number, "Welcome to NutriCoach! Please ask your nutritionist to register your number.")
        return

    @tool
    def get_food_nutrition(query: str) -> str:
        """Lookup calories and macros for a food item. Use product name only."""
        return json.dumps(lookup_food_nutrition(query))

    agent_executor = create_react_agent(model=llm, tools=[get_food_nutrition], prompt=GENERAL_SYSTEM_PROMPT)

    print("[General Agent] Generating response...")
    try:
        response = await asyncio.wait_for(
            agent_executor.ainvoke(
                {"messages": [("user", message_body)]},
                config={"recursion_limit": 8},
            ),
            timeout=25,
        )
        reply_text = response["messages"][-1].content
    except asyncio.TimeoutError:
        reply_text = "I am taking too long to process that. Please try a shorter message."
    except Exception as e:
        print("[General Agent] Agent invocation failed:", e)
        reply_text = "I hit a temporary issue. Please try again."

    print("[General Agent] Sending WhatsApp reply...")
    send_whatsapp_message(phone_number, reply_text)
