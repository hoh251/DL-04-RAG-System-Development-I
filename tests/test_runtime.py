"""Deterministic error-path tests; no paid provider is contacted."""
import os
import unittest
from unittest.mock import patch

import config
from src.generator import Generator, LLM, NoLLM, get_llm
from src.query_transform import QueryTransformer, normalize_query
from src.memory import ConversationMemory


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.test_credentials = patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only-not-a-real-key"})
        self.test_credentials.start()
        self.addCleanup(self.test_credentials.stop)

    def test_known_formal_word_is_not_duplicated(self):
        self.assertEqual(normalize_query("ถุงยางอนามัย"), "ถุงยางอนามัย")

    def test_aids_is_not_replaced_with_hiv(self):
        self.assertEqual(normalize_query("เอดส์"), "เอดส์")

    def test_cloud_model_must_be_explicit(self):
        with patch.object(config, "LLM_PROVIDER", "openai"), patch.object(config, "LLM_MODEL", ""):
            with self.assertRaisesRegex(ValueError, "RAG_LLM_MODEL"):
                LLM()

    def test_openai_key_missing(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(config, "LLM_PROVIDER", "openai"), patch.object(config, "LLM_MODEL", "explicit-test-model"):
            with self.assertRaisesRegex(ValueError, "Missing OPENAI_API_KEY"):
                LLM()

    def test_google_key_missing(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(config, "LLM_PROVIDER", "gemini"), patch.object(config, "LLM_MODEL", "explicit-test-model"):
            with self.assertRaisesRegex(ValueError, "Missing GOOGLE_API_KEY"):
                LLM()

    def test_gemini_key_alias(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-alias-not-a-real-key"}, clear=True), patch.object(config, "LLM_PROVIDER", "gemini"), patch.object(config, "LLM_MODEL", "gemini-3.5-flash-lite"), patch("src.generator.OpenAI") as client:
            LLM()
            self.assertEqual(client.call_args.kwargs["api_key"], "test-alias-not-a-real-key")

    def test_google_key_takes_priority(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-google", "GEMINI_API_KEY": "test-alias"}, clear=True), patch.object(config, "LLM_PROVIDER", "gemini"), patch("src.generator.OpenAI") as client:
            LLM()
            self.assertEqual(client.call_args.kwargs["api_key"], "test-google")

    def test_retired_gemini_rejected(self):
        for model in ["gemini-1.5-flash", "gemini-2.0-flash"]:
            with self.subTest(model=model), patch.object(config, "LLM_PROVIDER", "gemini"), patch.object(config, "LLM_MODEL", model):
                with self.assertRaisesRegex(ValueError, "retired"):
                    LLM()

    def test_ollama_does_not_need_an_api_key(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(config, "LLM_PROVIDER", "ollama"), patch.object(config, "LLM_MODEL", "qwen2.5:3b"), patch("src.generator.OpenAI") as client:
            LLM()
            self.assertEqual(client.call_args.kwargs["api_key"], "ollama")
            self.assertEqual(client.call_args.kwargs["max_retries"], 0)

    def test_unknown_provider(self):
        with patch.object(config, "LLM_PROVIDER", "invalid"):
            with self.assertRaises(ValueError):
                LLM()

    def test_openai_request_uses_completion_token_limit(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only-not-a-real-key"}), patch.object(config, "LLM_PROVIDER", "openai"), patch.object(config, "LLM_MODEL", "explicit-test-model"), patch("src.generator.OpenAI") as client:
            client.return_value.chat.completions.create.return_value.choices[0].message.content = "OK"
            self.assertEqual(LLM().chat([{"role": "user", "content": "test"}]), "OK")
            options = client.return_value.chat.completions.create.call_args.kwargs
            self.assertIn("max_completion_tokens", options)
            self.assertNotIn("temperature", options)

    def test_gemini_request_uses_compatible_endpoint(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only-not-a-real-key"}), patch.object(config, "LLM_PROVIDER", "gemini"), patch.object(config, "LLM_MODEL", "explicit-test-model"), patch("src.generator.OpenAI") as client:
            client.return_value.chat.completions.create.return_value.choices[0].message.content = "OK"
            LLM().chat([{"role": "user", "content": "test"}])
            self.assertEqual(client.call_args.kwargs["base_url"], "https://generativelanguage.googleapis.com/v1beta/openai/")
            self.assertIn("max_tokens", client.return_value.chat.completions.create.call_args.kwargs)
            self.assertEqual(client.return_value.chat.completions.create.call_args.kwargs["reasoning_effort"], "low")

    def test_empty_llm_output_is_failure(self):
        with patch("src.generator.OpenAI") as client:
            client.return_value.chat.completions.create.return_value.choices[0].message.content = ""
            with self.assertRaisesRegex(RuntimeError, "empty"):
                LLM().chat([{"role": "user", "content": "test"}])

    def test_no_context_never_calls_model(self):
        with patch("src.generator.LLM") as llm:
            result = Generator(llm).generate("test", [])
            self.assertTrue(result["no_context"])
            llm.chat.assert_not_called()

    def test_disabled_llm_is_explicit(self):
        with patch.object(config, "USE_LLM", False):
            self.assertIsInstance(get_llm(), NoLLM)

    def test_no_llm_cannot_fake_generation(self):
        with self.assertRaises(RuntimeError):
            NoLLM().chat([])

    def test_memory_is_bounded_and_resettable(self):
        memory = ConversationMemory()
        for number in range(20):
            memory.add_user(f"question {number}")
            memory.add_assistant(f"answer {number}")
        self.assertEqual(len(memory.messages), config.MEMORY_MAX_TURNS * 2)
        self.assertTrue(memory.first_topic)
        memory.clear()
        self.assertEqual(memory.get_context(), "")

    def test_extractive_mode_reports_itself(self):
        chunk = {"answer": "ตัวอย่างจากเอกสาร", "text": "ตัวอย่างจากเอกสาร",
                 "chunk_id": 0, "question": "ตัวอย่าง", "line_no": 1, "score": 0.9}
        result = Generator(NoLLM()).generate("ตัวอย่าง", [chunk])
        self.assertEqual(result["answer_mode"], "extractive")
        self.assertIn("[1]", result["answer"])

    def test_generation_failure_does_not_silently_pass(self):
        class BrokenLLM:
            def chat(self, messages):
                raise TimeoutError("simulated")
        with patch.object(config, "ALLOW_LLM_FALLBACK", False):
            with self.assertRaisesRegex(RuntimeError, "generation failed"):
                Generator(BrokenLLM()).generate("test", [{"answer": "example", "text": "example"}])

    def test_transform_failure_does_not_silently_pass(self):
        class BrokenLLM:
            def chat(self, messages):
                raise TimeoutError("simulated")
        with patch.object(config, "USE_LLM", True), patch.object(config, "USE_QUERY_TRANSFORM", True):
            with self.assertRaisesRegex(RuntimeError, "transformation failed"):
                QueryTransformer(BrokenLLM()).transform("test")


if __name__ == "__main__":
    unittest.main()
