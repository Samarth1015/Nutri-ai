import os
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)

def send_whatsapp_message(to_number: str, message_body: str):
    """Send a WhatsApp message using Twilio."""
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
    print(f"account_sid: {account_sid}")
    print(f"auth_token: {auth_token}")
    print(f"from_number: {from_number}")
    
    # If credentials are poor or not fully configured, fallback to console mock
    if not account_sid or not auth_token:
        logger.warning("Twilio credentials missing or using test keys. Mocking send.")
        print(f"\n[MOCK WHATSAPP SEND]")
        print(f"To: {to_number}")
        print(f"Message: {message_body}\n")
        return "mock_sid_12345"

    try:
        client = Client(account_sid, auth_token)
        # Ensure 'to_number' has 'whatsapp:' prefix
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"
            
        message = client.messages.create(
            from_=from_number,
            body=message_body,
            to=to_number
        )
        logger.info(f"Message sent successfully. SID: {message.sid}")
        return message.sid
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {e}")
        # Fallback to console for debugging
        print(f"\n[FAILED WHATSAPP -> CONSOLE FALLBACK]")
        print(f"To: {to_number}")
        print(f"Message: {message_body}\n")
        return None
