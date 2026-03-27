import re
import json
from datetime import datetime
from zoneinfo import ZoneInfo


def _normalize_text(text: str) -> str:
    value = (text or "").replace("\r\n", "\n").strip()
    lines = [line.rstrip() for line in value.split("\n")]
    value = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def _extract_metric(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def format_intake_reply(raw_reply: str, client_name: str, current_date: str | None = None) -> str:
    text = _normalize_text(raw_reply)
    if not text:
        text = "I have noted your update. Keep going!"

    if current_date is None:
        current_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")

    lower = text.lower()
    has_strong_structure = (
        "date" in lower
        and "client" in lower
        and ("logged items" in lower or "meals" in lower)
        and ("today's intake" in lower or "intake" in lower)
    )
    if has_strong_structure:
        return text

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    bullets = [line for line in lines if line.startswith("-")]
    if not bullets:
        bullets = ["- Logged from your latest message"]

    calories = _extract_metric(text, r"(\d+(?:\.\d+)?)\s*(?:kcal|calories)")
    protein = _extract_metric(text, r"(\d+(?:\.\d+)?)\s*g(?:\s*protein)?")
    calories_line = f"{calories} kcal" if calories else "Not available yet"
    protein_line = f"{protein} g" if protein else "Not available yet"

    guidance_line = next(
        (
            line
            for line in lines
            if not line.startswith("-")
            and ":" not in line[:18]
        ),
        "Nice work logging this. Stay consistent and keep sharing updates.",
    )

    return (
        f"Date: {current_date}\n"
        f"Client: {client_name}\n\n"
        f"Logged Items:\n"
        f"{chr(10).join(bullets[:5])}\n\n"
        f"Today's Intake:\n"
        f"- Calories: {calories_line}\n"
        f"- Protein: {protein_line}\n\n"
        f"Guidance:\n"
        f"{guidance_line}"
    )


def format_query_reply(raw_reply: str, nutritionist_name: str) -> str:
    text = _normalize_text(raw_reply)
    if not text:
        text = "I could not find enough data right now. Please try again."

    # If model returns JSON/text blob, convert to a simple conversational fallback.
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                pairs = [f"{k}: {v}" for k, v in parsed.items() if v not in [None, "", [], {}]]
                if pairs:
                    return (
                        f"I checked that for you, {nutritionist_name}.\n"
                        + "\n".join(f"- {line}" for line in pairs[:5])
                    )
            if isinstance(parsed, list):
                if not parsed:
                    return "I checked, but there is no matching data yet."
                return (
                    f"I checked that for you, {nutritionist_name}.\n"
                    + "\n".join(f"- {item}" for item in parsed[:5])
                )
        except json.JSONDecodeError:
            pass

    # Prefer natural model output directly; trim only if excessively long.
    if len(text) <= 700:
        return text

    clipped = text[:697].rstrip() + "..."
    return f"{clipped}\n\nIf you want, I can also share this as a day-wise breakdown."
