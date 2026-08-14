"""LLM 服务单测。"""

import unittest
from unittest.mock import MagicMock

from app.services.llm_service import LLMService, LLMServiceError


class LLMServiceTests(unittest.TestCase):
    def test_chat_returns_content(self):
        client = MagicMock()
        choice = MagicMock()
        choice.message.content = "  你好  "
        response = MagicMock()
        response.choices = [choice]
        client.chat.completions.create.return_value = response

        service = LLMService(client=client, model="deepseek-chat")
        text = service.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(text, "你好")

    def test_chat_empty_choices_raises(self):
        client = MagicMock()
        response = MagicMock()
        response.choices = []
        client.chat.completions.create.return_value = response
        service = LLMService(client=client, model="deepseek-chat")
        with self.assertRaises(LLMServiceError):
            service.chat([{"role": "user", "content": "hi"}])


if __name__ == "__main__":
    unittest.main()
