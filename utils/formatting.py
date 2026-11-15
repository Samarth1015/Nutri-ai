import re
import json
from datetime import datetime, timedelta
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


def _format_number(value: float) -> str:
    if abs(value - int(value)) < 1e-9:
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _safe_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_target_metric(text: str, metric_name: str) -> float | None:
    pattern = rf"{metric_name}\s*:\s*[^/\n]*/\s*(\d+(?:\.\d+)?)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return _safe_float(match.group(1))


def _extract_logged_items(text: str) -> list[str]:
    lines = [line.strip() for line in text.split("\n")]
    items: list[str] = []
    plain_lines: list[str] = []
    in_block = False
    found_block = False

    for line in lines:
        lower = line.lower()
        if lower.startswith("logged items"):
            in_block = True
            found_block = True
            continue
        if in_block and (
            lower.startswith("today's intake")
            or lower.startswith("requested day intake")
            or lower.startswith("guidance")
            or lower.startswith("date:")
            or lower.startswith("client:")
        ):
            break
        if in_block and line.startswith("-"):
            items.append(line)
        elif in_block and line:
            plain_lines.append(line)

    if items:
        return items

    if found_block:
        for line in plain_lines:
            if any(token in line.lower() for token in ["not available", "none", "no logs"]):
                return []
        if plain_lines:
            return [f"- {plain_lines[0]}"]
        return []

    fallback_bullets = [line.strip() for line in lines if line.strip().startswith("-")]
    return fallback_bullets[:5]


def _sum_macros_from_items(items: list[str]) -> tuple[float, float]:
    calories = 0.0
    protein = 0.0
    for item in items:
        if re.match(r"^-\s*(calories?|protein)\s*:\s*.*\/", item, re.IGNORECASE):
            continue
        cal_match = re.search(r"(\d+(?:\.\d+)?)\s*kcal", item, re.IGNORECASE)
        pro_match = re.search(r"(\d+(?:\.\d+)?)\s*g\s*protein", item, re.IGNORECASE)
        if cal_match:
            calories += _safe_float(cal_match.group(1)) or 0.0
        if pro_match:
            protein += _safe_float(pro_match.group(1)) or 0.0
    return calories, protein


def _extract_date_from_text(text: str) -> str | None:
    # Prefer explicit "Date: YYYY-MM-DD"
    date_line = re.search(r"^\s*date\s*:\s*(\d{4}-\d{2}-\d{2})\s*$", text, re.IGNORECASE | re.MULTILINE)
    if date_line:
        return date_line.group(1)

    # Fallback: any ISO date in body
    any_iso = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if any_iso:
        return any_iso.group(1)
    return None


def _infer_requested_date(message_body: str | None, current_date: str) -> str | None:
    text = (message_body or "").strip().lower()
    if not text:
        return None

    try:
        base_date = datetime.strptime(current_date, "%Y-%m-%d")
    except ValueError:
        return None

    if "day before yesterday" in text or "day before yest" in text:
        return (base_date - timedelta(days=2)).strftime("%Y-%m-%d")
    if "yesterday" in text:
        return (base_date - timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in text:
        return base_date.strftime("%Y-%m-%d")

    # Explicit ISO date in message
    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if iso_match:
        return iso_match.group(1)

    # dd/mm/yyyy or dd-mm-yyyy
    dmy_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", text)
    if dmy_match:
        day = int(dmy_match.group(1))
        month = int(dmy_match.group(2))
        year_raw = dmy_match.group(3)
        year = int(year_raw) if year_raw else base_date.year
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None

    # "for 27" or "on 27th"
    day_only = re.search(r"\b(?:for|on)\s+(\d{1,2})(?:st|nd|rd|th)?\b", text)
    if day_only:
        day = int(day_only.group(1))
        if 1 <= day <= 31:
            month = base_date.month
            year = base_date.year
            if day > base_date.day:
                month -= 1
                if month == 0:
                    month = 12
                    year -= 1
            try:
                return datetime(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                return None

    return None


def _is_historical_query(message_body: str | None, inferred_date: str | None, current_date: str) -> bool:
    text = (message_body or "").strip().lower()
    if not text:
        return False
    if any(keyword in text for keyword in ["yesterday", "day before yesterday", "day before yest", "last", "previous"]):
        return True
    if inferred_date and inferred_date != current_date:
        return True
    return False


def _extract_guidance(text: str) -> str:
    guidance_match = re.search(r"guidance\s*:\s*(.*)$", text, re.IGNORECASE | re.DOTALL)
    if guidance_match:
        guidance = guidance_match.group(1).strip()
        if guidance:
            return guidance.split("\n")[0].strip()

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines:
        lower = line.lower()
        if line.startswith("-"):
            continue
        if lower.startswith(("date:", "client:", "logged items", "today's intake", "requested day intake", "guidance:")):
            continue
        return line
    return "Nice work logging this. Stay consistent and keep sharing updates."


def format_intake_reply(
    raw_reply: str,
    client_name: str,
    current_date: str | None = None,
    message_body: str | None = None,
    target_calories: float | None = None,
    target_protein_g: float | None = None,
) -> str:
    text = _normalize_text(raw_reply)
    if not text:
        text = "I have noted your update. Keep going!"

    if current_date is None:
        current_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")

    requested_date = _infer_requested_date(message_body, current_date)
    date_from_model = _extract_date_from_text(text)
    display_date = requested_date or date_from_model or current_date
    historical = _is_historical_query(message_body, requested_date, current_date)
    intake_title = "Requested Day Intake" if historical else "Today's Intake"

    items = _extract_logged_items(text)
    if not items:
        items = ["- None"]

    parsed_calories = _safe_float(_extract_metric(text, r"(?mi)^\s*-\s*calories?\s*:\s*(\d+(?:\.\d+)?)\s*/"))
    parsed_protein = _safe_float(_extract_metric(text, r"(?mi)^\s*-\s*protein\s*:\s*(\d+(?:\.\d+)?)\s*/"))
    items_calories, items_protein = _sum_macros_from_items(items)

    total_calories = parsed_calories if parsed_calories is not None else items_calories
    total_protein = parsed_protein if parsed_protein is not None else items_protein
    total_calories = total_calories if total_calories is not None else 0.0
    total_protein = total_protein if total_protein is not None else 0.0

    cal_target = (
        _safe_float(target_calories)
        if target_calories is not None
        else _extract_target_metric(text, "calories")
    )
    pro_target = (
        _safe_float(target_protein_g)
        if target_protein_g is not None
        else _extract_target_metric(text, "protein")
    )
    cal_target = cal_target if cal_target is not None else 0.0
    pro_target = pro_target if pro_target is not None else 0.0

    guidance_line = _extract_guidance(text)
    if total_calories > 8000 or total_protein > 500:
        guidance_line = (
            f"{guidance_line} The totals look unusually high for one day, so there may be a logging error."
        )

    return (
        f"Date: {display_date}\n"
        f"Client: {client_name}\n\n"
        f"Logged Items:\n"
        f"{chr(10).join(items[:8])}\n\n"
        f"{intake_title}:\n"
        f"- Calories: {_format_number(total_calories)} / {_format_number(cal_target)} kcal\n"
        f"- Protein: {_format_number(total_protein)} / {_format_number(pro_target)}g\n\n"
        f"Guidance:\n"
        f"{guidance_line}"
    )


def _is_greeting_message(message_body: str | None) -> bool:
    text = (message_body or "").strip().lower()
    if not text:
        return False
    if text in {"hi", "hey", "hello", "hii", "yo"}:
        return True
    return bool(re.match(r"^(hi|hey|hello)\b[\s!.?]*$", text))


def _is_important_query(message_body: str | None) -> bool:
    text = (message_body or "").strip().lower()
    if not text:
        return False
    keywords = [
        "record",
        "progress",
        "diet",
        "eat",
        "intake",
        "target",
        "today",
        "yesterday",
        "week",
        "day",
        "calorie",
        "protein",
        "client",
        "for",
        "march",
    ]
    return any(keyword in text for keyword in keywords)


def _extract_client_hint(message_body: str | None, text: str) -> str | None:
    stopwords = {
        "today",
        "yesterday",
        "past",
        "last",
        "day",
        "days",
        "week",
        "month",
        "record",
        "progress",
        "target",
        "calories",
        "protein",
        "intake",
        "diet",
    }

    msg = (message_body or "").strip()
    candidate_patterns = [
        r"\b(?:for|of|about)\s+([A-Za-z][A-Za-z0-9_-]{1,30})\b",
        r"\bclient\s+([A-Za-z][A-Za-z0-9_-]{1,30})\b",
    ]
    for pattern in candidate_patterns:
        match = re.search(pattern, msg, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate.lower() not in stopwords:
                return candidate.title()

    possessive_match = re.search(r"\b([A-Z][a-z]+)'s\b", text)
    if possessive_match:
        return possessive_match.group(1)
    return None


def _extract_targets_from_text(text: str) -> tuple[float, float, float | None, float | None] | None:
    # Example: "Shiva's daily targets are 1000 calories, 120g of protein, 200g of carbs, and 60g of fat."
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*calories?.*?"
        r"(\d+(?:\.\d+)?)\s*g\s*(?:of\s*)?protein.*?"
        r"(\d+(?:\.\d+)?)\s*g\s*(?:of\s*)?carbs?.*?"
        r"(\d+(?:\.\d+)?)\s*g\s*(?:of\s*)?fat",
        text,
        re.IGNORECASE,
    )
    if match:
        return (
            _safe_float(match.group(1)) or 0.0,
            _safe_float(match.group(2)) or 0.0,
            _safe_float(match.group(3)),
            _safe_float(match.group(4)),
        )

    fallback = re.search(
        r"calories?\s*[:=]?\s*(\d+(?:\.\d+)?)\D+protein\s*[:=]?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    if fallback:
        return (_safe_float(fallback.group(1)) or 0.0, _safe_float(fallback.group(2)) or 0.0, None, None)
    return None


def _extract_key_points(text: str) -> list[str]:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    bullet_like = [line.lstrip("- ").strip() for line in lines if line.startswith("-") or re.match(r"^\d+\.", line)]
    if bullet_like:
        return bullet_like[:8]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    points = [s.strip().rstrip(".") for s in sentences if s.strip()]
    return points[:6]


def _has_macro_anomaly(text: str) -> bool:
    if "logging/parsing error" in text.lower() or "unusually high" in text.lower():
        return True

    calorie_matches: list[str] = []
    protein_matches: list[str] = []

    for pattern in [r"(\d+(?:\.\d+)?)\s*calories?", r"calories?\s*[:=]?\s*(\d+(?:\.\d+)?)"]:
        calorie_matches.extend(re.findall(pattern, text, re.IGNORECASE))

    for pattern in [
        r"(\d+(?:\.\d+)?)\s*g\s*protein",
        r"protein(?:\s*intake)?\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g?",
    ]:
        protein_matches.extend(re.findall(pattern, text, re.IGNORECASE))

    max_cal = max((_safe_float(v) or 0.0) for v in calorie_matches) if calorie_matches else 0.0
    max_pro = max((_safe_float(v) or 0.0) for v in protein_matches) if protein_matches else 0.0
    return max_cal > 8000 or max_pro > 500


def _infer_period_hint(message_body: str | None) -> str | None:
    text = (message_body or "").strip().lower()
    if not text:
        return None

    now = datetime.utcnow()

    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if iso_match:
        return iso_match.group(1)

    dmy_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", text)
    if dmy_match:
        day = int(dmy_match.group(1))
        month = int(dmy_match.group(2))
        year_raw = dmy_match.group(3)
        year = int(year_raw) if year_raw else now.year
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None

    past_days = re.search(r"\bpast\s+(\d+)\s+days?\b", text)
    if past_days:
        return f"Last {past_days.group(1)} days"

    if "day before yesterday" in text or "day before yest" in text:
        return (now - timedelta(days=2)).strftime("%Y-%m-%d")
    if "yesterday" in text:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in text:
        return now.strftime("%Y-%m-%d")
    return None


def format_query_reply(raw_reply: str, nutritionist_name: str, message_body: str | None = None) -> str:
    text = _normalize_text(raw_reply)
    if not text:
        text = "I could not find enough data right now. Please try again."

    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                pairs = [f"{k}: {v}" for k, v in parsed.items() if v not in [None, "", [], {}]]
                if pairs:
                    text = "\n".join(pairs[:8])
            elif isinstance(parsed, list):
                if not parsed:
                    return "I checked, but there is no matching data yet."
                text = "\n".join(str(item) for item in parsed[:8])
        except json.JSONDecodeError:
            pass

    if _is_greeting_message(message_body):
        return text

    # Keep well-structured model outputs unchanged.
    if text.lower().startswith("nutricoach update"):
        return text

    client_hint = _extract_client_hint(message_body, text)
    period_hint = _infer_period_hint(message_body)
    anomaly = _has_macro_anomaly(text)
    important = _is_important_query(message_body)

    targets = _extract_targets_from_text(text) if (message_body and "target" in message_body.lower()) else None
    if targets:
        calories, protein, carbs, fat = targets
        lines = ["NutriCoach Update"]
        if client_hint:
            lines.append(f"Client: {client_hint}")
        if period_hint:
            lines.append(f"Period: {period_hint}")
        lines.extend(
            [
                "",
                "Targets:",
                f"- Calories: {_format_number(calories)} kcal/day",
                f"- Protein: {_format_number(protein)}g/day",
            ]
        )
        if carbs is not None:
            lines.append(f"- Carbs: {_format_number(carbs)}g/day")
        if fat is not None:
            lines.append(f"- Fat: {_format_number(fat)}g/day")
        lines.extend(
            [
                "",
                "Alerts:",
                "- Potential logging/parsing issue present in recent data." if anomaly else "- None",
            ]
        )
        return "\n".join(lines)

    if important:
        points = _extract_key_points(text)
        if not points:
            return text

        lines = ["NutriCoach Update"]
        if client_hint:
            lines.append(f"Client: {client_hint}")
        if period_hint:
            lines.append(f"Period: {period_hint}")
        lines.extend(["", "Key Points:"])
        for index, point in enumerate(points[:8], start=1):
            clean_point = re.sub(r"^\d+\.\s*", "", point).strip()
            if anomaly and re.search(r"\b(doing great|excellent|perfect)\b", clean_point, re.IGNORECASE):
                clean_point = re.sub(
                    r"\bhas been doing great,\s*with\b",
                    "Weekly summary:",
                    clean_point,
                    flags=re.IGNORECASE,
                )
                clean_point = re.sub(
                    r"\bdoing great,\s*with\b",
                    "Weekly summary:",
                    clean_point,
                    flags=re.IGNORECASE,
                )
                clean_point = re.sub(
                    r"\b(doing great|excellent|perfect)\b,?\s*",
                    "",
                    clean_point,
                    flags=re.IGNORECASE,
                ).strip()
                clean_point = re.sub(
                    r"^([A-Za-z]+)\s+Weekly summary:\s*",
                    r"Weekly summary for \1: ",
                    clean_point,
                )
            lines.append(f"{index}. {clean_point}")

        lines.extend(
            [
                "",
                "Alerts:",
                "- Potential logging/parsing issue present in macro totals." if anomaly else "- None",
            ]
        )
        return "\n".join(lines)

    if len(text) <= 700:
        return text

    clipped = text[:697].rstrip() + "..."
    return f"{clipped}\n\nIf you want, I can also share this as a day-wise breakdown."
