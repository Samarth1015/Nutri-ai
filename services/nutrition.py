import os
from fatsecret import Fatsecret

consumer_key = os.getenv("CLIENT_ID_FOOD")
consumer_secret = os.getenv("CLIENT_SECRET_FOOD")

fs = Fatsecret(consumer_key, consumer_secret)


def fetch_nutrition_data_sync(query: str) -> dict:
    """Fetch nutrition data from FatSecret API."""
    try:
        # Search for the food item
        foods = fs.foods_search(query,region="India",language="English")
        
        if not foods:
            return {"error": "Food not found"}
            
        # Get the first food item
        food_id = foods[0]["food_id"]
        food_data = fs.food_get(food_id)
        
        # Extract serving sizes
        servings = food_data.get("servings", {}).get("serving", [])
        if not isinstance(servings, list):
            servings = [servings]
            
        # Get serving with 100g
        serving_100g = None
        for serving in servings:
            if serving.get("metric_serving_unit") == "g" and serving.get("metric_serving_qty") == 100:
                serving_100g = serving
                break
        
        # Fallback to first serving if 100g not found
        if not serving_100g:
            serving_100g = servings[0]
            
        return {
            "foods": [
                {
                    "food_name": food_data.get("food_name"),
                    "brand_name": food_data.get("brand_name"),
                    "serving_size": f"{serving_100g.get('metric_serving_qty')} {serving_100g.get('metric_serving_unit')}",
                    "calories": float(serving_100g.get("calories", 0)),
                    "protein_g": float(serving_100g.get("protein", 0)),
                    "carbs_g": float(serving_100g.get("total_carbohydrate", 0)),
                    "fat_g": float(serving_100g.get("total_fat", 0)),
                }
            ]
        }
    except Exception as e:
        return {"error": str(e)}


async def fetch_nutrition_data(query: str) -> dict:
    """Async wrapper for agents that use async tool definitions."""
    return fetch_nutrition_data_sync(query)
