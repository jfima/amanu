import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from amanu.providers.openrouter.utils import fetch_openrouter_models
from amanu.wizard import ProviderManager

class TestOpenRouterIntegration(unittest.TestCase):
    
    @patch('amanu.providers.openrouter.utils.requests.get')
    def test_fetch_models(self, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "test/model-1",
                    "name": "Test Model 1",
                    "context_length": 1000,
                    "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                    "top_provider": {"max_completion_tokens": 500}
                }
            ]
        }
        mock_get.return_value = mock_response
        
        models = fetch_openrouter_models("fake_key")
        
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["name"], "test/model-1")
        self.assertEqual(models[0]["cost_per_1M_tokens_usd"]["input"], 1.0)
        self.assertEqual(models[0]["cost_per_1M_tokens_usd"]["output"], 2.0)

    @patch('amanu.wizard.yaml.dump')
    @patch('amanu.wizard.open')
    def test_provider_manager_update(self, mock_open, mock_yaml_dump):
        # Mock ProviderManager to avoid loading real files
        with patch('amanu.wizard.ProviderManager._load_providers') as mock_load:
            mock_load.return_value = {
                "openrouter": {
                    "models": []
                }
            }
            manager = ProviderManager()
            
            new_models = [{"name": "new-model", "type": "refinement"}]
            manager.update_provider_models("openrouter", new_models)
            
            self.assertEqual(manager.providers["openrouter"]["models"], new_models)
            # Verify yaml dump was called
            mock_yaml_dump.assert_called()

if __name__ == '__main__':
    unittest.main()
