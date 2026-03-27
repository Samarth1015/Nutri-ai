from fastapi import APIRouter, Request, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from db.database import get_db
from api.router import identify_sender
from agents.intake_agent import run_intake_agent
from agents.query_agent import run_query_agent
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.form()
    sender_phone = data.get("From")
    message_body = data.get("Body")

    if not sender_phone or not message_body:
        raise HTTPException(status_code=400, detail="Missing 'From' or 'Body' in form data")

    # Identify: is this a client or a nutritionist?
    sender_type, sender_obj = identify_sender(db, sender_phone)

    from graph.graph_builder import build_graph
    
    app_graph = build_graph()
    state = {
        "sender_phone": sender_phone,
        "sender_type": sender_type,
        "raw_message": message_body,
        "sender_id": sender_obj.id if sender_obj else 0,
        "current_step": "start",
        "messages": []
    }

    await app_graph.ainvoke(state)
    
    # Twilio expects a 200 OK and valid TwiML for a reply, or empty response if we reply async
    return Response(content="<Response></Response>", media_type="application/xml")
