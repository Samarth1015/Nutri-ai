import json
import os
import re
import sys
from ast import literal_eval
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

from mcp.server.fastmcp import FastMCP

# Add parent path to import db
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import SessionLocal
from db.models import Client, MealLog
from services.nutrition import fetch_nutrition_data_sync

# Setup FastMCP
mcp = FastMCP("nutricoach-db-tools")

FALLBACK_NUTRITION_PER_SERVING = {
    "beer": {"calories": 153, "protein_g": 1.6, "carbs_g": 13.0, "fat_g": 0.0},
    "egg": {"calories": 78, "protein_g": 6.3, "carbs_g": 0.6, "fat_g": 5.3},
    "rice": {"calories": 130, "protein_g": 2.7, "carbs_g": 28.0, "fat_g": 0.3},
    "kurkure": {"calories": 240, "protein_g": 3.0, "carbs_g": 28.0, "fat_g": 13.0},
}


@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _load_parsed_payload(parsed_data: Any) -> dict:
    if isinstance(parsed_data, dict):
        return parsed_data
    if isinstance(parsed_data, str):
        try:
            loaded = json.loads(parsed_data)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _clean_food_query(raw_query: Any) -> str:
    """
    Normalize food lookup input to product name only.
    Examples:
    - "2 beer" -> "beer"
    - "{'query': '1 plate paneer'}" -> "paneer"
    """
    extracted = raw_query

    if isinstance(raw_query, dict):
        extracted = raw_query.get("query") or raw_query.get("food") or raw_query.get("item")
    elif isinstance(raw_query, str):
        text = raw_query.strip()
        if text.startswith("{") and text.endswith("}"):
            parsed_obj = None
            try:
                parsed_obj = json.loads(text)
            except json.JSONDecodeError:
                try:
                    parsed_obj = literal_eval(text)
                except (ValueError, SyntaxError):
                    parsed_obj = None
            if isinstance(parsed_obj, dict):
                extracted = parsed_obj.get("query") or parsed_obj.get("food") or parsed_obj.get("item") or text
            else:
                extracted = text
        else:
            extracted = text

    text = str(extracted or "").strip().lower()
    text = re.sub(r"\s+", " ", text)

    # Remove leading quantity and common measurement words.
    text = re.sub(
        r"^\s*\d+(?:[.,]\d+)?\s*(?:x|cups?|cup|plates?|plate|bowl|bowls|ml|l|lit(?:er|re)?s?|grams?|g|kg|oz|tbsp|tsp|slices?|slice|bottles?|bottle|cans?|can|pieces?|piece)?\b\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove optional connector after quantity.
    text = re.sub(r"^\s*(?:of)\s+", "", text, flags=re.IGNORECASE)

    # Keep only safe food phrase characters.
    text = re.sub(r"[^a-z0-9\s\-\+]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _fallback_profile(query: str) -> dict:
    if query in FALLBACK_NUTRITION_PER_SERVING:
        return FALLBACK_NUTRITION_PER_SERVING[query]
    singular = query[:-1] if query.endswith("s") else query
    if singular in FALLBACK_NUTRITION_PER_SERVING:
        return FALLBACK_NUTRITION_PER_SERVING[singular]
    for key, profile in FALLBACK_NUTRITION_PER_SERVING.items():
        if key in query:
            return profile
    return {}


def _quantity_multiplier(quantity: Any, fallback_text: str = "") -> tuple[float, Any]:
    source = str(quantity if quantity not in [None, ""] else fallback_text or "").strip().lower()
    if not source:
        return 1.0, quantity

    match = re.search(r"(\d+(?:[.,]\d+)?)", source)
    if not match:
        return 1.0, quantity

    try:
        qty_value = float(match.group(1).replace(",", "."))
    except ValueError:
        return 1.0, quantity

    if qty_value <= 0:
        qty_value = 1.0

    if "kg" in source:
        return qty_value * 10.0, quantity if quantity not in [None, ""] else f"{qty_value} kg"
    if re.search(r"\bg\b", source):
        return qty_value / 100.0, quantity if quantity not in [None, ""] else f"{qty_value} g"
    if "ml" in source:
        return qty_value / 100.0, quantity if quantity not in [None, ""] else f"{qty_value} ml"
    if re.search(r"\bl\b|\bliter\b|\blitre\b", source):
        return qty_value * 10.0, quantity if quantity not in [None, ""] else f"{qty_value} l"

    return qty_value, quantity if quantity not in [None, ""] else qty_value


def _lookup_item_nutrition(cleaned_query: str, nutrition_cache: dict[str, dict]) -> dict:
    if not cleaned_query:
        return {}

    candidates = [cleaned_query]
    if cleaned_query.endswith("s") and len(cleaned_query) > 2:
        candidates.append(cleaned_query[:-1])

    for candidate in candidates:
        if candidate not in nutrition_cache:
            nutrition_cache[candidate] = fetch_nutrition_data_sync(candidate)
        result = nutrition_cache[candidate]
        foods = result.get("foods", []) if isinstance(result, dict) else []
        first_food = foods[0] if isinstance(foods, list) and foods else None
        if isinstance(first_food, dict):
            return first_food

    return _fallback_profile(cleaned_query)


def _coerce_meal_item(item: Any, nutrition_cache: dict[str, dict]) -> dict | None:
    """
    Normalize meal item payload and backfill macros via nutrition lookup when missing.
    """
    if isinstance(item, str):
        raw_name = str(item).strip()
        name = _clean_food_query(raw_name)
        meal: dict[str, Any] = {"name": name, "quantity": None}
        quantity_source_text = raw_name
    elif isinstance(item, dict):
        raw_name = str(
            item.get("name")
            or item.get("food_name")
            or item.get("item")
            or item.get("food")
            or item.get("title")
            or ""
        ).strip()
        name = raw_name
        meal = dict(item)
        meal["name"] = str(name).strip()
        quantity_source_text = raw_name
    else:
        return None

    meal_name = str(meal.get("name") or "").strip()
    quantity = meal.get("quantity")
    quantity_factor, normalized_quantity = _quantity_multiplier(quantity, quantity_source_text)
    meal["quantity"] = normalized_quantity
    query_source = f"{normalized_quantity} {meal_name}" if normalized_quantity not in [None, ""] else meal_name
    cleaned_query = _clean_food_query(query_source)

    calories = _safe_float(meal.get("calories"))
    protein = _safe_float(meal.get("protein_g", meal.get("protein")))
    carbs = _safe_float(meal.get("carbs_g", meal.get("carbs", meal.get("carbohydrates"))))
    fat = _safe_float(meal.get("fat_g", meal.get("fat")))
    has_macros = any(value > 0 for value in [calories, protein, carbs, fat])

    if not has_macros and cleaned_query:
        first_food = _lookup_item_nutrition(cleaned_query, nutrition_cache)
        if isinstance(first_food, dict):
            calories = _safe_float(first_food.get("calories")) * quantity_factor
            protein = _safe_float(first_food.get("protein_g", first_food.get("protein"))) * quantity_factor
            carbs = _safe_float(first_food.get("carbs_g", first_food.get("carbs"))) * quantity_factor
            fat = _safe_float(first_food.get("fat_g", first_food.get("fat"))) * quantity_factor
            meal_name = meal_name or str(first_food.get("food_name") or cleaned_query).strip()
    elif has_macros and quantity_factor > 1 and not re.search(r"\d", meal_name):
        # LLM often returns per-unit macros with a separate quantity field.
        calories *= quantity_factor
        protein *= quantity_factor
        carbs *= quantity_factor
        fat *= quantity_factor

    meal["name"] = meal_name or cleaned_query or "unknown"
    meal["food"] = meal["name"]
    meal["calories"] = calories
    meal["protein_g"] = protein
    meal["carbs_g"] = carbs
    meal["fat_g"] = fat
    return meal


@mcp.tool()
def log_meal(client_id: int, raw_message: str, parsed_data: str) -> dict:
    """
    Log a client's meal entry.
    `parsed_data` can be a JSON string or dictionary with a `meals` list.
    """
    parsed_json = _load_parsed_payload(parsed_data)
    meals = parsed_json.get("meals", [])
    if (not meals) and parsed_json.get("items"):
        meals = parsed_json.get("items", [])
        parsed_json["meals"] = meals
    if isinstance(meals, dict):
        meals = [meals]
    if not isinstance(meals, list):
        meals = []

    nutrition_cache: dict[str, dict] = {}
    normalized_meals = []
    for meal in meals:
        normalized = _coerce_meal_item(meal, nutrition_cache)
        if normalized:
            normalized_meals.append(normalized)
    parsed_json["meals"] = normalized_meals

    with get_db_session() as db:
        total_cal = sum(_safe_float(item.get("calories")) for item in normalized_meals if isinstance(item, dict))
        total_pro = sum(_safe_float(item.get("protein_g")) for item in normalized_meals if isinstance(item, dict))
        total_carb = sum(_safe_float(item.get("carbs_g")) for item in normalized_meals if isinstance(item, dict))
        total_fat = sum(_safe_float(item.get("fat_g")) for item in normalized_meals if isinstance(item, dict))

        workout = parsed_json.get("workout") or {}
        if isinstance(workout, dict):
            workout_notes = workout.get("type")
        else:
            workout_notes = str(workout) if workout else None

        raw_user_message = str(raw_message or "").strip()

        meal_log = MealLog(
            client_id=client_id,
            raw_message=raw_user_message,
            parsed_meals=parsed_json,
            total_calories=total_cal,
            total_protein_g=total_pro,
            total_carbs_g=total_carb,
            total_fat_g=total_fat,
            workout_notes=workout_notes,
            weight_kg=parsed_json.get("weight_kg", parsed_json.get("weight")),
        )
        db.add(meal_log)
        db.commit()
        db.refresh(meal_log)

        return {
            "success": True,
            "log_id": meal_log.id,
            "raw_message": meal_log.raw_message,
            "total_calories": round(total_cal, 2),
            "total_protein_g": round(total_pro, 2),
        }


@mcp.tool()
def lookup_food_nutrition(query: str) -> dict:
    """Lookup calories and macros for a food query using the nutrition service."""
    cleaned_query = _clean_food_query(query)
    if not cleaned_query:
        return {"error": "Query is required"}
    result = fetch_nutrition_data_sync(cleaned_query)
    if isinstance(result, dict):
        result["normalized_query"] = cleaned_query
    return result


@mcp.tool()
def query_client_logs(client_id: int, days: int = 7) -> list:
    """Get a client's meal logs for the past N days."""
    cutoff_date = datetime.utcnow() - timedelta(days=max(1, days))
    with get_db_session() as db:
        logs = (
            db.query(MealLog)
            .filter(MealLog.client_id == client_id, MealLog.logged_at >= cutoff_date)
            .order_by(MealLog.logged_at.desc())
            .all()
        )
        return [
            {
                "id": log.id,
                "logged_at": str(log.logged_at),
                "raw_message": log.raw_message,
                "total_calories": log.total_calories,
                "total_protein_g": log.total_protein_g,
            }
            for log in logs
        ]


@mcp.tool()
def get_client_by_phone(phone: str) -> dict:
    """Look up a client by WhatsApp phone number (normalized, e.g., +919876543210)."""
    with get_db_session() as db:
        client = db.query(Client).filter(Client.phone_number == phone).first()
        if not client:
            return {"error": "Client not found"}
        return {
            "id": client.id,
            "name": client.name,
            "phone_number": client.phone_number,
            "target_calories": client.target_calories,
            "target_protein_g": client.target_protein_g,
            "target_carbs_g": client.target_carbs_g,
            "target_fat_g": client.target_fat_g,
        }


@mcp.tool()
def get_client_info(client_id: int) -> dict:
    """Get a client's profile and targets."""
    with get_db_session() as db:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return {"error": "Client not found"}
        return {
            "id": client.id,
            "name": client.name,
            "phone_number": client.phone_number,
            "target_calories": client.target_calories,
            "target_protein_g": client.target_protein_g,
            "target_carbs_g": client.target_carbs_g,
            "target_fat_g": client.target_fat_g,
        }


@mcp.tool()
def search_clients_by_name(nutritionist_id: int, name_query: str, limit: int = 5) -> list:
    """Find clients by partial name for a nutritionist. Useful for fuzzy client matching."""
    query = (name_query or "").strip()
    if not query:
        return []
    clamped_limit = max(1, min(limit, 20))
    with get_db_session() as db:
        clients = (
            db.query(Client)
            .filter(
                Client.nutritionist_id == nutritionist_id,
                Client.name.ilike(f"%{query}%"),
            )
            .order_by(Client.name.asc())
            .limit(clamped_limit)
            .all()
        )
        return [{"id": c.id, "name": c.name, "phone_number": c.phone_number} for c in clients]


@mcp.tool()
def update_client_targets(client_id: int, target_calories: int, target_protein_g: int) -> dict:
    """Update a client's daily calorie and protein targets."""
    with get_db_session() as db:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return {"error": "Client not found"}

        client.target_calories = target_calories
        client.target_protein_g = target_protein_g
        db.commit()
        db.refresh(client)

        return {
            "success": True,
            "message": f"Updated targets for {client.name}",
            "new_target_calories": client.target_calories,
            "new_target_protein_g": client.target_protein_g,
        }


@mcp.tool()
def get_weekly_summary(client_id: int) -> dict:
    """Calculate past 7-day averages and compliance score."""
    cutoff_date = datetime.utcnow() - timedelta(days=7)
    with get_db_session() as db:
        logs = db.query(MealLog).filter(MealLog.client_id == client_id, MealLog.logged_at >= cutoff_date).all()
        if not logs:
            return {"error": "No logs found for the past 7 days"}

        avg_calories = sum(_safe_float(log.total_calories) for log in logs) / len(logs)
        avg_protein = sum(_safe_float(log.total_protein_g) for log in logs) / len(logs)

        client = db.query(Client).filter(Client.id == client_id).first()
        calorie_compliance = 0.0
        protein_compliance = 0.0
        if client and client.target_calories and avg_calories > 0:
            calorie_compliance = min(100.0, (avg_calories / client.target_calories) * 100)
        if client and client.target_protein_g and avg_protein > 0:
            protein_compliance = min(100.0, (avg_protein / client.target_protein_g) * 100)

        compliance_values = [value for value in [calorie_compliance, protein_compliance] if value > 0]
        compliance_score = sum(compliance_values) / len(compliance_values) if compliance_values else 0.0

        return {
            "avg_calories": round(avg_calories, 2),
            "avg_protein": round(avg_protein, 2),
            "compliance_score": round(compliance_score, 2),
            "calorie_compliance_pct": round(calorie_compliance, 2),
            "protein_compliance_pct": round(protein_compliance, 2),
            "days_logged": len(logs),
        }


@mcp.tool()
def get_client_daily_summary(client_id: int, date: str) -> dict:
    """Get totals and entries for a specific client and date (YYYY-MM-DD)."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

    next_date = target_date + timedelta(days=1)
    with get_db_session() as db:
        logs = (
            db.query(MealLog)
            .filter(
                MealLog.client_id == client_id,
                MealLog.logged_at >= target_date,
                MealLog.logged_at < next_date,
            )
            .order_by(MealLog.logged_at.asc())
            .all()
        )
        if not logs:
            return {"client_id": client_id, "date": date, "entries": 0, "message": "No logs found"}

        logged_items = []
        for log in logs:
            parsed = log.parsed_meals if isinstance(log.parsed_meals, dict) else {}
            meals = parsed.get("meals", [])
            if isinstance(meals, dict):
                meals = [meals]
            for meal in meals:
                if isinstance(meal, dict):
                    logged_items.append(meal)

        return {
            "client_id": client_id,
            "date": date,
            "entries": len(logs),
            "total_calories": round(sum(_safe_float(log.total_calories) for log in logs), 2),
            "total_protein_g": round(sum(_safe_float(log.total_protein_g) for log in logs), 2),
            "raw_messages": [log.raw_message for log in logs if log.raw_message],
            "logged_items": logged_items,
        }


@mcp.tool()
def flag_nutritional_gaps(client_id: int) -> list:
    """Identify past 7-day entries where calorie target was significantly missed."""
    cutoff_date = datetime.utcnow() - timedelta(days=7)
    with get_db_session() as db:
        logs = db.query(MealLog).filter(MealLog.client_id == client_id, MealLog.logged_at >= cutoff_date).all()
        client = db.query(Client).filter(Client.id == client_id).first()

        if not client or not client.target_calories:
            return [{"error": "Client or targets not found"}]

        flagged_days = []
        for log in logs:
            cal = _safe_float(log.total_calories)
            if cal < (client.target_calories * 0.7) or cal > (client.target_calories * 1.3):
                flagged_days.append(
                    {
                        "date": str(log.logged_at.date()),
                        "calories": cal,
                        "target": client.target_calories,
                        "reason": "Too low" if cal < client.target_calories else "Too high",
                    }
                )
        return flagged_days


@mcp.tool()
def list_nutritionist_clients(nutritionist_id: int) -> list:
    """Get all active clients for a nutritionist."""
    with get_db_session() as db:
        clients = db.query(Client).filter(Client.nutritionist_id == nutritionist_id).all()
        return [{"id": c.id, "name": c.name, "phone_number": c.phone_number} for c in clients]


@mcp.tool()
def list_clients_missing_logs(nutritionist_id: int, days_without_logs: int = 3) -> list:
    """List clients with no logs for the past N days."""
    threshold_days = max(1, days_without_logs)
    cutoff_date = datetime.utcnow() - timedelta(days=threshold_days)
    now = datetime.utcnow()

    with get_db_session() as db:
        clients = db.query(Client).filter(Client.nutritionist_id == nutritionist_id).all()
        missing_clients = []
        for client in clients:
            latest_log = (
                db.query(MealLog)
                .filter(MealLog.client_id == client.id)
                .order_by(MealLog.logged_at.desc())
                .first()
            )
            last_logged_at = latest_log.logged_at if latest_log else None
            if not last_logged_at or last_logged_at < cutoff_date:
                days_since = None if not last_logged_at else (now - last_logged_at).days
                missing_clients.append(
                    {
                        "client_id": client.id,
                        "client_name": client.name,
                        "last_logged_at": str(last_logged_at) if last_logged_at else None,
                        "days_since_last_log": days_since,
                    }
                )

        missing_clients.sort(
            key=lambda row: row["days_since_last_log"] if row["days_since_last_log"] is not None else 10_000,
            reverse=True,
        )
        return missing_clients


if __name__ == "__main__":
    mcp.run(transport="stdio")
