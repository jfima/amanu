import argparse
import os
import time
import google.generativeai as genai
from pathlib import Path
import yaml

def load_config():
    """Load configuration to get API key."""
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("Error: config.yaml not found.")
        return None
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def count_tokens(file_path):
    """Uploads file and counts tokens using Gemini API."""
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"Error: File {file_path} not found.")
        return

    print(f"Uploading {file_path.name}...")
    try:
        # Upload file
        file = genai.upload_file(file_path)
        
        # Wait for processing
        print("Processing file...")
        while file.state.name == "PROCESSING":
            time.sleep(1)
            file = genai.get_file(file.name)
            
        if file.state.name == "FAILED":
            print(f"Error: File processing failed with state {file.state.name}")
            return

        print(f"File ready: {file.uri}")
        
        # Count tokens
        # We need to specify a model. Using gemini-2.0-flash as default.
        model_name = "gemini-2.0-flash"
        model = genai.GenerativeModel(model_name)
        
        print(f"Counting tokens with model {model_name}...")
        response = model.count_tokens([file])
        
        print(f"\n--- Results for {file_path.name} ---")
        print(f"Total Tokens: {response.total_tokens}")
        print(f"Model Limit (Input): 1,048,576")
        print(f"Percentage of Context: {response.total_tokens / 1048576 * 100:.2f}%")
        
        # Cleanup
        print("\nCleaning up remote file...")
        file.delete()
        print("Done.")

    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    parser = argparse.ArgumentParser(description="Count tokens in an audio file using Gemini API.")
    parser.add_argument("file", help="Path to the audio file")
    args = parser.parse_args()

    config = load_config()
    if not config:
        return

    api_key = config.get("gemini", {}).get("api_key")
    if not api_key:
        print("Error: API key not found in config.yaml")
        return

    genai.configure(api_key=api_key)
    
    count_tokens(args.file)

if __name__ == "__main__":
    main()
