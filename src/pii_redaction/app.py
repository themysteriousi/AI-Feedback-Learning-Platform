"""
PII Redaction & Feedback Processing Lambda
------------------------------------------
Triggered by DynamoDB Streams whenever a new feedback record is inserted.
Steps:
  1. Parse the new DynamoDB record from the stream event.
  2. Redact PII from prompt and response text using Microsoft Presidio.
  3. Write the clean, redacted record as JSON to the S3 Data Lake.

Dependencies (bundled in Lambda Layer or container):
  - presidio-analyzer
  - presidio-anonymizer
  - boto3 (built-in in Lambda)
"""

import json
import os
import boto3
from decimal import Decimal
from datetime import datetime

# Lazy-import Presidio so it only loads when needed
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    # Fallback: log warning — Presidio not installed in this environment
    PRESIDIO_AVAILABLE = False
    print("WARNING: Presidio not available. PII will NOT be redacted.")

# Initialize AWS clients
s3 = boto3.client("s3")

# Get config from environment variables (set in Terraform)
DATA_LAKE_BUCKET = os.environ["DATA_LAKE_BUCKET"]
DATA_LAKE_PREFIX = os.environ.get("DATA_LAKE_PREFIX", "feedback/raw/")

# Initialize Presidio engines once (outside handler for warm Lambda reuse)
analyzer = AnalyzerEngine() if PRESIDIO_AVAILABLE else None
anonymizer = AnonymizerEngine() if PRESIDIO_AVAILABLE else None

# Fields in the DynamoDB record that may contain PII
PII_FIELDS = ["prompt", "response", "user_comment"]


def redact_pii(text: str) -> str:
    """
    Detects and anonymizes PII entities in a text string using Presidio.
    Replaces detected entities with their entity type label, e.g. <PERSON>.
    """
    if not PRESIDIO_AVAILABLE or not text:
        return text

    results = analyzer.analyze(text=text, language="en")
    anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
    return anonymized.text


def parse_dynamodb_record(record: dict) -> dict:
    """
    Converts a DynamoDB Stream record's NewImage (which uses DynamoDB JSON types)
    into a plain Python dictionary.
    """
    from boto3.dynamodb.types import TypeDeserializer
    deserializer = TypeDeserializer()
    return {
        key: deserializer.deserialize(value)
        for key, value in record.items()
    }


def json_serial(obj):
    """JSON serializer for objects not serializable by default json library."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def lambda_handler(event, context):
    processed_count = 0
    error_count = 0

    for record in event.get("Records", []):
        # Only process INSERT and MODIFY events, skip REMOVE
        if record.get("eventName") not in ("INSERT", "MODIFY"):
            continue

        try:
            # 1. Parse the raw DynamoDB record
            raw_item = record["dynamodb"].get("NewImage", {})
            item = parse_dynamodb_record(raw_item)

            # 2. Redact PII from sensitive text fields
            for field in PII_FIELDS:
                if field in item and isinstance(item[field], str):
                    original = item[field]
                    item[field] = redact_pii(original)
                    item[f"{field}_pii_redacted"] = True  # Audit flag

            # 3. Add processing metadata
            item["processed_at"] = datetime.utcnow().isoformat()
            item["pii_redaction_engine"] = "presidio" if PRESIDIO_AVAILABLE else "none"

            # 4. Build a partitioned S3 key (year/month/day) for Athena compatibility
            now = datetime.utcnow()
            s3_key = (
                f"{DATA_LAKE_PREFIX}"
                f"year={now.year}/month={now.month:02d}/day={now.day:02d}/"
                f"{item.get('session_id', 'unknown')}_{item.get('timestamp', now.isoformat())}.json"
            )

            # 5. Write to S3 Data Lake
            s3.put_object(
                Bucket=DATA_LAKE_BUCKET,
                Key=s3_key,
                Body=json.dumps(item, default=json_serial),
                ContentType="application/json",
            )

            print(f"[OK] Written to s3://{DATA_LAKE_BUCKET}/{s3_key}")
            processed_count += 1

        except Exception as e:
            error_count += 1
            print(f"[ERROR] Failed to process record: {e}")
            # Do NOT re-raise — we don't want to block the stream for one bad record

    return {
        "statusCode": 200,
        "body": json.dumps({
            "processed": processed_count,
            "errors": error_count
        })
    }
