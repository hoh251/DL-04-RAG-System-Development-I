import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import config
from gemini_preflight import check_gemini


class GeminiPreflightTests(unittest.TestCase):
    def setUp(self):
        self.provider = patch.object(config, "LLM_PROVIDER", "gemini")
        self.model = patch.object(config, "LLM_MODEL", "gemini-3.5-flash-lite")
        self.provider.start()
        self.model.start()
        self.addCleanup(self.provider.stop)
        self.addCleanup(self.model.stop)

    def test_missing_key_does_not_call_network(self):
        with patch.dict(os.environ, {}, clear=True), patch("gemini_preflight.urlopen") as network:
            result = check_gemini()
            self.assertEqual(result["status"], "missing_key")
            self.assertFalse(result["inference_tested"])
            network.assert_not_called()

    def test_model_discovery_does_not_claim_inference(self):
        payload = {"models": [{"name": "models/gemini-3.5-flash-lite", "supportedGenerationMethods": ["generateContent"]}]}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy-secret"}, clear=True), patch("gemini_preflight.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as network:
            result = check_gemini()
            self.assertEqual(result["status"], "ready")
            self.assertFalse(result["inference_tested"])
            self.assertNotIn("dummy-secret", json.dumps(result))
            self.assertNotIn("dummy-secret", network.call_args.args[0].full_url)

    def test_unavailable_model_is_not_replaced_silently(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy-secret"}, clear=True), patch("gemini_preflight.urlopen", return_value=io.BytesIO(b'{"models": []}')):
            self.assertEqual(check_gemini()["status"], "model_unavailable")

    def test_auth_failure_does_not_save_provider_body(self):
        error = HTTPError("https://generativelanguage.googleapis.com/v1beta/models", 403, "dummy-secret", {}, None)
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy-secret"}, clear=True), patch("gemini_preflight.urlopen", side_effect=error):
            result = check_gemini()
            self.assertEqual(result["http_status"], 403)
            self.assertNotIn("dummy-secret", json.dumps(result))

    def test_network_error_is_explicit(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy-secret"}, clear=True), patch("gemini_preflight.urlopen", side_effect=URLError("offline")):
            self.assertEqual(check_gemini()["status"], "network_error")
