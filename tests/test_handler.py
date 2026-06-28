import json
import unittest
from importlib import import_module
from unittest.mock import patch

handler = import_module("app.lambda.handler")


class HandlerTests(unittest.TestCase):
    def test_classify_high_prompt_without_bedrock(self):
        prompt = "Design a scalable multi-region architecture and analyze trade-offs."
        self.assertEqual(handler.classify(prompt), "HIGH")

    def test_classify_medium_prompt_without_bedrock(self):
        prompt = "Please summarize this article in a few bullet points."
        self.assertEqual(handler.classify(prompt), "MEDIUM")

    def test_handler_returns_400_for_missing_prompt(self):
        event = {"body": json.dumps({})}
        response = handler.handler(event, None)
        self.assertEqual(response["statusCode"], 400)

    @patch.object(handler, "call_llm", return_value="hello")
    @patch.object(handler.dynamo_table, "put_item")
    def test_handler_returns_response(self, put_item_mock, call_llm_mock):
        event = {"body": json.dumps({"prompt": "What is AWS?"})}
        response = handler.handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertIn(payload["tier"], {"HIGH", "MEDIUM", "LOW"})
        self.assertEqual(payload["response"], "hello")
        put_item_mock.assert_called_once()
        call_llm_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
