import unittest
from unittest.mock import patch

import gemma_api


class GemmaApiTests(unittest.TestCase):
    def test_prompt_requests_gender_neutral_language(self):
        prompt = gemma_api._prompt("Editor", 121)

        self.assertIn("gender-neutral", prompt)
        self.assertIn("'bro'", prompt)
        self.assertIn("'dude'", prompt)

    def test_generate_roast_prefers_ollama(self):
        with patch("gemma_api._generate_with_ollama", return_value="One. Two."), patch(
            "gemma_api._generate_with_huggingface"
        ) as fallback:
            self.assertEqual(gemma_api.generate_roast("Editor", 121), "One. Two.")
            fallback.assert_not_called()

    def test_generate_roast_falls_back_on_ollama_timeout(self):
        with patch(
            "gemma_api._generate_with_ollama",
            side_effect=gemma_api.requests.Timeout("offline"),
        ), patch(
            "gemma_api._generate_with_huggingface",
            return_value="Fallback roast.",
        ):
            self.assertEqual(
                gemma_api.generate_roast("Browser", 125),
                "Fallback roast. Now go touch real grass.",
            )

    def test_huggingface_fallback_reads_chat_completion_content(self):
        response = type(
            "Response",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {"message": type("Message", (), {"content": "Chat roast."})()},
                    )()
                ]
            },
        )()
        client = type("Client", (), {"chat_completion": lambda *args, **kwargs: response})()
        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}), patch(
            "gemma_api.InferenceClient", return_value=client
        ):
            self.assertEqual(gemma_api._generate_with_huggingface("Prompt"), "Chat roast.")


if __name__ == "__main__":
    unittest.main()
