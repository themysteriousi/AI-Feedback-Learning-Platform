"""
Feedback Writer Lambda
-----------------------
Called by the frontend after a user rates an AI response.
Writes both explicit feedback (stars, like/dislike, comments)
and implicit signals (session duration, re-reads) into DynamoDB.
DynamoDB Streams will automatically trigger the PII Redaction Lambda downstream.
"""

import json
import os
import uuid
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["FEEDBACK_TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))

        # --- Validate required fields ---
        prompt = body.get("prompt", "").strip()
        response = body.get("response", "").strip()
        if not prompt or not response:
            return _response(400, {"error": "Both 'prompt' and 'response' are required."})

        # --- Build the feedback record ---
        record = {
            # Primary key
            "session_id": body.get("session_id", str(uuid.uuid4())),
            "timestamp":  datetime.now(timezone.utc).isoformat(),

            # Core interaction data
            "prompt":       prompt,
            "response":     response,
            "model_id":     body.get("model_id", "unknown"),

            # Explicit feedback signals
            "star_rating":    body.get("star_rating"),       # int 1-5
            "thumbs":         body.get("thumbs"),            # "up" | "down"
            "accuracy_rating": body.get("accuracy_rating"),  # int 1-5
            "relevance_rating": body.get("relevance_rating"),# int 1-5
            "user_comment":   body.get("user_comment", ""),

            # Implicit feedback signals (from frontend telemetry)
            "session_duration_secs":    body.get("session_duration_secs"),
            "reread_count":             body.get("reread_count", 0),
            "followup_question_count":  body.get("followup_question_count", 0),
            "query_reformulation_count": body.get("query_reformulation_count", 0),
            "conversation_abandoned":   body.get("conversation_abandoned", False),

            # Metadata
            "feedback_version": "1.0",
        }

        # Strip None values to keep DynamoDB records clean
        record = {k: v for k, v in record.items() if v is not None}

        # Write to DynamoDB (this automatically triggers the DynamoDB Stream)
        table.put_item(Item=record)

        return _response(200, {
            "message": "Feedback recorded successfully.",
            "session_id": record["session_id"]
        })

    except Exception as e:
        print(f"[ERROR] {e}")
        return _response(500, {"error": "Internal server error."})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
