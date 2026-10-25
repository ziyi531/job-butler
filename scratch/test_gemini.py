import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
print(f"API Key exists: {bool(api_key)}")
if api_key:
    print(f"API Key prefix: {api_key[:6]}...")
    genai.configure(api_key=api_key)
    try:
        print("Listing models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Model name: {m.name}, Display name: {m.display_name}")
    except Exception as e:
        print(f"Error listing models: {e}")
else:
    print("No GEMINI_API_KEY environment variable found.")
