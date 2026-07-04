import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: No API Key found in .env file.")
    print("Please set GOOGLE_API_KEY or GEMINI_API_KEY in your .env file.")
    raise SystemExit(1)

print("Connecting to Google Gemini API...")

url = "https://generativelanguage.googleapis.com/v1beta/models"

try:
    response = requests.get(url, headers={"x-goog-api-key": api_key}, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print("\nSUCCESS! Connection established.\n")
        print("Available Models:")
        print("-" * 40)
        found_flash = False
        flash_models = []
        for model in data.get("models", []):
            if "flash" in model.get("name", ""):
                print(f"- {model['name']}")
                found_flash = True
                flash_models.append(model["name"].removeprefix("models/"))
        print("-" * 40)

        if found_flash:
            print("\nChoose an available model appropriate for your deployment.")
            print(f"Example: OPENAI_MODEL_NAME={flash_models[0]}")
        else:
            print("\nWARNING: No 'flash' model found. Check your API key permissions.")
    else:
        print(f"\nAPI request failed. Status Code: {response.status_code}")
        print("Error Message:")
        print(response.text)
        raise SystemExit(1)
except Exception as exc:
    print(f"\nRequest failed: {exc}")
    raise SystemExit(1)
