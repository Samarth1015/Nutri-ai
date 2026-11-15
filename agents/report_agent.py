from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agents.model_config import get_agent_model
from services.whatsapp import send_whatsapp_message
from mcp_servers.server import flag_nutritional_gaps, get_weekly_summary, list_nutritionist_clients, lookup_food_nutrition

@tool
def fetch_clients(nutritionist_id: int) -> list:
    """Get all active clients for a given nutritionist ID."""
    return list_nutritionist_clients(nutritionist_id)

@tool
def fetch_weekly_summary(client_id: int) -> dict:
    """Get weekly summary data for a specific client."""
    return get_weekly_summary(client_id)

@tool
def fetch_nutritional_gaps(client_id: int) -> list:
    """Get nutritional gaps for a specific client across the last 7 days."""
    return flag_nutritional_gaps(client_id)

@tool
def fetch_food_nutrition(query: str) -> dict:
    """Lookup calories and macros for a food query when report generation needs food-level context. Use product name only."""
    return lookup_food_nutrition(query)

@tool
def send_report_to_whatsapp(nutritionist_phone: str, report_text: str) -> str:
    """Sends the formatted weekly report text via WhatsApp to the nutritionist."""
    send_whatsapp_message(nutritionist_phone, report_text)
    return "Message sent successfully"

async def run_report_agent(nutritionist_obj):
    """Generates weekly report for all clients autonomously via ReAct agent."""
    print(f"[Report Agent] Starting autonomous report generation for {nutritionist_obj.name}")
    
    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(model=get_agent_model("REPORT_AGENT"), temperature=0)
    except Exception as e:
        print("[Report Agent] Groq error: ", e)
        return
        
    tools = [fetch_clients, fetch_weekly_summary, fetch_nutritional_gaps, fetch_food_nutrition, send_report_to_whatsapp]

    system_prompt = f"""
You are an autonomous dietitian assistant managing weekly reports for '{nutritionist_obj.name}' (ID: {nutritionist_obj.id}, Phone: {nutritionist_obj.phone_number}).

Your job is to execute the following pipeline strictly autonomously:
1. Call `fetch_clients` to get all of the nutritionist's clients.
2. For EVERY client returned, gather their data by calling both `fetch_weekly_summary` and `fetch_nutritional_gaps`.
3. Analyze the data and write a structured weekly report for the client formatted like this:
   1. Client Overview (name, compliance score)
   2. Day-by-Day Observations
   3. Key Observations (Did they miss targets?)
   4. Recommendations for next week
4. Instantly invoke `send_report_to_whatsapp` to deliver that specific client's report to the nutritionist's phone number.

You must not stop until you have completely processed and sent a report for ALL clients. 
You are fully autonomous. Do not ask for user input. If a client has no data or errors, note that gently in their report and send it anyway.
"""
    
    # create_react_agent automatically binds tools to the LLM and orchestrates the ToolNode execution loop
    agent_executor = create_react_agent(llm, tools, messages_modifier=system_prompt)
    
    print("[Report Agent] Kickstarting agent tool execution loop...")
    inputs = {"messages": [("user", "Start generating and sending the weekly reports now.")]}
    
    # Run the autonomous execution block
    response = await agent_executor.ainvoke(inputs)
    
    print(f"[Report Agent] Execution complete. Final agent thought: {response['messages'][-1].content}")
