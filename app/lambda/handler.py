import json
import os
import re
import uuid
from datetime import datetime, timezone

AWS_REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")
LOG_TABLE_NAME = os.environ.get("LOG_TABLE_NAME", "prompt_logs")

# Model identifiers (Bedrock model IDs)
MODELS = {
    "HIGH": "anthropic.claude-opus-4-6",
    "MEDIUM": "anthropic.claude-sonnet-4-6",
    "LOW": "anthropic.claude-haiku-4-5-20251001",
}

COMPLEXITY_HINTS = {
    "HIGH": [
        r"\bdesign\b",
        r"\barchitecture\b",
        r"\banalyze\b",
        r"\bcompare\b",
        r"\btrade[- ]?off\b",
        r"\bproof\b",
        r"\boptimiz",
        r"\bdebug\b",
        r"\bsecurity\b",
        r"\bmigrate\b",
        r"\bimplement\b.*\bfrom scratch\b",
    ],
    "MEDIUM": [
        r"\bsummar",
        r"\bexplain\b",
        r"\bwrite\b",
        r"\bdraft\b",
        r"\brewrite\b",
        r"\bplan\b",
        r"\bconvert\b",
    ],
    "LOW": [
        r"\bwhat is\b",
        r"\bdefine\b",
        r"\blist\b",
        r"\bformat\b",
        r"\bclassify\b",
        r"\bfix\b.*\btypo\b",
    ],
}


def _json_response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Content-Type": "application/json",
        },
        "body": json.dumps(payload),
    }


def _extract_prompt(event):
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raise ValueError("Base64 encoded bodies are not supported.")

    payload = json.loads(body)
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")

    prompt = prompt.strip()
    if not prompt:
        raise ValueError("prompt is required")
    return prompt


def _keyword_score(prompt, tier):
    text = prompt.lower()
    score = 0
    for pattern in COMPLEXITY_HINTS[tier]:
        if re.search(pattern, text):
            score += 1
    return score


def classify(prompt):
    high_score = _keyword_score(prompt, "HIGH")
    medium_score = _keyword_score(prompt, "MEDIUM")
    low_score = _keyword_score(prompt, "LOW")

    if high_score >= 2:
        return "HIGH"
    if high_score == 1 and medium_score == 0:
        return "HIGH"
    if medium_score >= 1:
        return "MEDIUM"
    if low_score >= 1:
        return "LOW"

    # Fallback to a lightweight Bedrock classification via LangChain only if heuristics fail.
    try:
        from langchain_aws.chat_models import ChatBedrock
    except Exception:
        # LangChain not available in test environment; default to MEDIUM
        return "MEDIUM"

    classifier = ChatBedrock(model_id=MODELS["LOW"], region_name=AWS_REGION)
    prompt_msg = (
        "Classify the prompt complexity as HIGH, MEDIUM, or LOW. "
        "Respond with exactly one word. Prompt: " + prompt
    )
    resp = classifier.generate([{"role": "user", "content": prompt_msg}])
    text = getattr(resp, "generations", [{}])[0].get("text", "").strip().upper()
    return text if text in MODELS else "MEDIUM"


def call_llm(prompt, tier):
    # Use LangChain's ChatBedrock wrapper to call Bedrock. Lazy-import so tests can run
    try:
        from langchain_aws.chat_models import ChatBedrock
    except Exception:
        raise RuntimeError("LangChain/ChatBedrock is not installed in this environment")

    client = ChatBedrock(model_id=MODELS[tier], region_name=AWS_REGION)
    resp = client.generate([{"role": "user", "content": prompt}])
    # `generate` returns a complex object; extract text defensively
    try:
        return getattr(resp, "generations", [{}])[0].get("text", "")
    except Exception:
        return str(resp)


def handler(event, context):
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return _json_response(200, {"message": "ok"})

    try:
        prompt = _extract_prompt(event)
        tier = classify(prompt)
        reply = call_llm(prompt, tier)
        # Lazy import boto3 and write to DynamoDB so tests that don't have boto3 installed can run
        try:
            import boto3

            dynamo_table = boto3.resource("dynamodb", region_name=AWS_REGION).Table(LOG_TABLE_NAME)
            dynamo_table.put_item(
                Item={
                    "id": str(uuid.uuid4()),
                    "tier": tier,
                    "prompt": prompt,
                    "response": reply,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            # If boto3 isn't available in the test environment, skip persisting
            pass
        return _json_response(200, {"tier": tier, "response": reply})
    except ValueError as exc:
        return _json_response(400, {"error": str(exc)})
    except Exception as exc:  # pragma: no cover - surfaced via CloudWatch in AWS
        return _json_response(500, {"error": "Internal server error", "detail": str(exc)})
