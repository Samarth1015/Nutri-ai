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
