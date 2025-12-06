import requests
from typing import List, Dict, Any, Optional

def fetch_openrouter_models(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches available models from OpenRouter API.
    
    Args:
        api_key: Optional API key. If not provided, tries to read from environment.
                 Note: OpenRouter models endpoint is public, but using a key might be safer for rate limits.
    
    Returns:
        List of model definitions in Amanu format.
    """
    url = "https://openrouter.ai/api/v1/models"
    headers = {}
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        models = []
        for item in data.get("data", []):
            # Extract relevant fields
            model_id = item.get("id")
            name = item.get("name", model_id)
            context_length = item.get("context_length", 0)
            pricing = item.get("pricing", {})
            
            # Calculate cost per 1M tokens
            # OpenRouter pricing is usually per token (or per 1K/1M depending on display, but API returns raw float per token)
            # We need to verify the unit. The docs say "prompt": "0.00000005" which is per token.
            # So for 1M tokens, we multiply by 1,000,000.
            
            input_cost_per_token = float(pricing.get("prompt", 0))
            output_cost_per_token = float(pricing.get("completion", 0))
            
            input_cost_1m = input_cost_per_token * 1_000_000
            output_cost_1m = output_cost_per_token * 1_000_000
            
            # Determine capabilities based on architecture or description
            # This is heuristic-based as OpenRouter doesn't strictly categorize "transcription" vs "refinement"
            # We'll assume all text models can do refinement.
            # Multimodal models can do transcription if they support audio input, but that's hard to know from this endpoint alone usually.
            # However, for now we will return a generic structure and let the caller filter/augment.
            
            model_def = {
                "name": model_id, # Use ID as the technical name
                "display_name": name,
                "context_window": {
                    "input_tokens": context_length,
                    "output_tokens": item.get("top_provider", {}).get("max_completion_tokens", 4096) # Estimate or fallback
                },
                "cost_per_1M_tokens_usd": {
                    "input": round(input_cost_1m, 6),
                    "output": round(output_cost_1m, 6)
                }
            }
            models.append(model_def)
            
        return models
        
    except Exception as e:
        print(f"Error fetching OpenRouter models: {e}")
        return []
