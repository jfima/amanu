import unittest
from unittest.mock import MagicMock, patch
import requests
from amanu.providers.ollama.provider import OllamaClient, OllamaConfig

class TestOllamaErrors(unittest.TestCase):
    def setUp(self):
        self.config = OllamaConfig(
            base_url="http://localhost:11434",
            timeout=10,
            auto_pull_models=False, # Now ignored effectively
            transcription_model="whisper",
            refinement_model="llama3"
        )
        self.client = OllamaClient(self.config)

    @patch('requests.Session.get')
    def test_check_connection_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        self.assertTrue(self.client.check_connection())

    @patch('requests.Session.get')
    def test_check_connection_failure_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        # Should return False and log error (not crashing)
        self.assertFalse(self.client.check_connection())

    @patch('requests.Session.get')
    def test_check_connection_failure_status_code(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        self.assertFalse(self.client.check_connection())

    @patch('amanu.providers.ollama.provider.OllamaClient.list_models')
    def test_ensure_model_exists_exact(self, mock_list):
        mock_list.return_value = ["llama3", "mistral"]
        # Should pass without error
        self.assertTrue(self.client.ensure_model("llama3"))

    @patch('amanu.providers.ollama.provider.OllamaClient.list_models')
    def test_ensure_model_exists_normalized(self, mock_list):
        mock_list.return_value = ["llama3:latest", "mistral"]
        # Should match "llama3" to "llama3:latest"
        self.assertTrue(self.client.ensure_model("llama3"))

    @patch('amanu.providers.ollama.provider.OllamaClient.list_models')
    def test_ensure_model_missing_raises_error(self, mock_list):
        mock_list.return_value = ["mistral"]
        
        with self.assertRaises(RuntimeError) as context:
            self.client.ensure_model("llama3")
        
        error_msg = str(context.exception)
        self.assertIn("not found", error_msg)
        self.assertIn("ollama pull llama3", error_msg)

if __name__ == '__main__':
    unittest.main()
