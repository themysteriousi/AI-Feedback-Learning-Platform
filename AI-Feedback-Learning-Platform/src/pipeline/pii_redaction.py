"""
Module 3: PII Redaction Pipeline
Uses Microsoft Presidio (open-source) to detect and redact
Personally Identifiable Information before writing to the S3 Data Lake.
"""
import json
import boto3
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from loguru import logger

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()
s3 = boto3.client("s3")


def redact_pii(text: str, language: str = "en") -> str:
    """Detect and redact PII entities from text using Microsoft Presidio."""
    results = analyzer.analyze(text=text, language=language)
    anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
    return anonymized.text


def process_feedback_record(record: dict, s3_bucket: str, s3_prefix: str = "feedback/") -> None:
    """Redact PII from a feedback record and write it to the S3 Data Lake."""
    interaction_id = record.get("interaction_id", "unknown")

    # Redact PII from prompt and response
    clean_record = {
        **record,
        "prompt": redact_pii(record.get("prompt", "")),
        "response": redact_pii(record.get("response", "")),
        "pii_redacted": True,
    }

    s3_key = f"{s3_prefix}{interaction_id}.json"
    s3.put_object(
        Bucket=s3_bucket,
        Key=s3_key,
        Body=json.dumps(clean_record),
        ContentType="application/json"
    )
    logger.info(f"PII-redacted record written to s3://{s3_bucket}/{s3_key}")


def lambda_handler(event: dict, context) -> dict:
    """AWS Lambda entry point triggered by DynamoDB Streams."""
    s3_bucket = "ai-feedback-data-lake"

    for record in event.get("Records", []):
        if record.get("eventName") in ("INSERT", "MODIFY"):
            new_image = record["dynamodb"].get("NewImage", {})
            feedback_record = {k: list(v.values())[0] for k, v in new_image.items()}
            try:
                process_feedback_record(feedback_record, s3_bucket)
            except Exception as e:
                logger.error(f"Failed to process record: {e}")

    return {"statusCode": 200, "body": "Pipeline executed successfully."}
