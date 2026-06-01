"""
Module 1: AI Interaction Engine
Handles inference requests to Amazon Bedrock and logs
prompt/response pairs to DynamoDB for feedback collection.
"""
import json
import boto3
import uuid
import time
from datetime import datetime
from typing import Optional
from loguru import logger

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")


def invoke_bedrock(prompt: str, model_id: str, max_tokens: int = 1024) -> str:
    """Send a prompt to Amazon Bedrock and return the generated response."""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    })
    response = bedrock.invoke_model(body=body, modelId=model_id)
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def log_interaction(
    interaction_id: str,
    prompt: str,
    response: str,
    model_id: str,
    latency_ms: int,
    table_name: str = "ai-feedback-store"
) -> None:
    """Store a prompt/response pair in DynamoDB for future feedback collection."""
    table = dynamodb.Table(table_name)
    table.put_item(Item={
        "interaction_id": interaction_id,
        "timestamp": datetime.utcnow().isoformat(),
        "prompt": prompt,
        "response": response,
        "model_id": model_id,
        "latency_ms": latency_ms,
        "feedback_score": None,
        "feedback_type": None,
    })
    logger.info(f"Logged interaction {interaction_id} to DynamoDB.")


def lambda_handler(event: dict, context) -> dict:
    """AWS Lambda entry point for the inference handler."""
    body = json.loads(event.get("body", "{}"))
    prompt = body.get("prompt", "")
    model_id = body.get("model_id", "anthropic.claude-3-sonnet-20240229-v1:0")

    if not prompt:
        return {"statusCode": 400, "body": json.dumps({"error": "prompt is required"})}

    interaction_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        response_text = invoke_bedrock(prompt, model_id)
        latency_ms = int((time.time() - start_time) * 1000)
        log_interaction(interaction_id, prompt, response_text, model_id, latency_ms)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "interaction_id": interaction_id,
                "response": response_text,
                "latency_ms": latency_ms,
            })
        }
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
