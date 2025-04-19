import os
import requests # To make API calls
import re       # For basic text cleaning
from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# --- Configuration ---
# 🚨 WARNING: Hardcoding API keys is insecure and NOT recommended for production!
SPOONACULAR_API_KEY = "e80cc912e2b34618bd8ad8f5d72e4849" # YOUR KEY - KEEP SECRET IN REAL APPS
FIND_INGREDIENTS_URL = "https://api.spoonacular.com/recipes/findByIngredients"
RECIPE_INFO_URL = "https://api.spoonacular.com/recipes/{id}/information" # New URL for details

if not SPOONACULAR_API_KEY:
    print("Error: SPOONACULAR_API_KEY is missing!")

# --- Helper Function ---
def clean_ingredient(name):
    if not isinstance(name, str): return ""
    name = name.lower().strip()
    name = re.sub(r'\s+', ' ', name)
    return name

# --- API Route: Find Recipes by Ingredients ---
@app.route('/api/find-recipes', methods=['GET'])
def find_recipes():
    ingredients_raw = request.args.get('ingredients', '')
    if not ingredients_raw: return jsonify({"error": "No ingredients provided"}), 400

    ingredients_list = [clean_ingredient(ing) for ing in ingredients_raw.split(',') if clean_ingredient(ing)]
    if not ingredients_list: return jsonify({"error": "No valid ingredients after cleaning"}), 400

    ingredients_query = ",".join(ingredients_list)
    print(f"Searching Spoonacular (findByIngredients) for: {ingredients_query}")

    params = {
        'ingredients': ingredients_query, 'number': 12, 'limitLicense': True,
        'ranking': 1, 'ignorePantry': True, 'apiKey': SPOONACULAR_API_KEY
    }

    try:
        response = requests.get(FIND_INGREDIENTS_URL, params=params, timeout=15)
        response.raise_for_status()
        recipes_data = response.json()

        formatted_recipes = []
        for recipe in recipes_data:
            used_ingredients_list = recipe.get('usedIngredients', []) or []
            missed_ingredients_list = recipe.get('missedIngredients', []) or []
            formatted_recipes.append({
                'id': recipe.get('id'), 'title': recipe.get('title'), 'image': recipe.get('image'),
                'usedIngredientCount': recipe.get('usedIngredientCount'),
                'missedIngredientCount': recipe.get('missedIngredientCount'),
                'usedIngredients': [ing.get('name') for ing in used_ingredients_list],
                'missedIngredients': [ing.get('name') for ing in missed_ingredients_list],
            })
        return jsonify(formatted_recipes)

    except requests.exceptions.Timeout:
        print("Error: Spoonacular API (findByIngredients) request timed out.")
        return jsonify({"error": "Recipe service request timed out. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        print(f"Error calling Spoonacular API (findByIngredients): {e}")
        status_code = getattr(e.response, 'status_code', 500)
        error_message = f"Could not connect to recipe service ({status_code})."
        # Add specific messages based on status code
        if status_code == 402: error_message = "API limit likely reached. Please check your Spoonacular account or try again later."
        elif status_code == 401: error_message = "Invalid API Key configured in backend."
        return jsonify({"error": error_message}), status_code
    except Exception as e:
        print(f"An unexpected error occurred in find_recipes: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500


# --- *** NEW API ROUTE: Get Recipe Details by ID *** ---
@app.route('/api/recipe-details/<int:recipe_id>', methods=['GET'])
def get_recipe_details(recipe_id):
    if not recipe_id:
        return jsonify({"error": "Recipe ID not provided"}), 400

    print(f"Fetching Spoonacular (Recipe Info) for ID: {recipe_id}")
    api_url = RECIPE_INFO_URL.format(id=recipe_id)
    params = {
        'includeNutrition': False, # Set to True if you want nutrition data (might cost more points)
        'apiKey': SPOONACULAR_API_KEY
    }

    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX, 5XX)

        # Directly return the JSON data from Spoonacular for this recipe
        recipe_details = response.json()
        return jsonify(recipe_details)

    except requests.exceptions.Timeout:
        print(f"Error: Spoonacular API (Recipe Info ID: {recipe_id}) request timed out.")
        return jsonify({"error": "Recipe detail service request timed out."}), 504
    except requests.exceptions.HTTPError as e:
         print(f"HTTP Error calling Spoonacular API (Recipe Info ID: {recipe_id}): {e}")
         status_code = e.response.status_code
         if status_code == 404:
             return jsonify({"error": f"Recipe with ID {recipe_id} not found."}), 404
         elif status_code == 402:
              return jsonify({"error": "API limit likely reached fetching details."}), 402
         elif status_code == 401:
              return jsonify({"error": "Invalid API Key configured."}), 401
         else:
              return jsonify({"error": f"Could not fetch recipe details (HTTP {status_code})."}), status_code
    except requests.exceptions.RequestException as e:
        # Catch other request errors (connection, etc.)
        print(f"Request Error calling Spoonacular API (Recipe Info ID: {recipe_id}): {e}")
        return jsonify({"error": "Could not connect to recipe detail service."}), 503 # Service Unavailable
    except Exception as e:
        print(f"An unexpected error occurred in get_recipe_details for ID {recipe_id}: {e}")
        return jsonify({"error": "An internal server error occurred fetching recipe details."}), 500


# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True, port=5001) # Keep debug=True for development ONLY