from graph.state import AgentState

def supervisor_node(state: AgentState) -> dict:
    """
    Decides which agent handles this message.
    - Client message → intake_agent
    - Nutritionist message → query_agent
    - Scheduled trigger → report_agent
    """
    if state.get("sender_type") == "client":
        return {"current_step": "intake"}
    elif state.get("sender_type") == "nutritionist":
        return {"current_step": "query"}
    else:
        return {"current_step": "general"}
