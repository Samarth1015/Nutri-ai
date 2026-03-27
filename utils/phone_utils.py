def normalize_phone(phone: str) -> str:
    """Normalize phone number by stripping 'whatsapp:' prefix."""
    if not phone:
        return ""
    if phone.startswith("whatsapp:"):
        return phone.replace("whatsapp:", "")
    return phone
