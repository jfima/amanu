import google.generativeai as genai
from utils import load_config
import os

def list_models():
    config = load_config()
    api_key = os.getenv("GEMINI_API_KEY") or config['gemini']['api_key']
    
    if not api_key or api_key == "YOUR_KEY_HERE":
        print("Error: API Key not found. Please check config.yaml")
        return

    genai.configure(api_key=api_key)
    
    print("Listing available models...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
