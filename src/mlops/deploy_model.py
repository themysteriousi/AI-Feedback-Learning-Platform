"""
Model Deployment Script
------------------------
After DPO fine-tuning on Colab, run this script to update your
Inference Lambda to point to the newly trained model on Hugging Face Hub.

It also records the deployment in a manifest file on S3, giving you
a full deployment history for auditability and rollback.

Usage:
  python deploy_model.py \
      --hf-repo    your-username/ai-feedback-model \
      --bucket     your-data-lake-bucket \
      --function   ai-feedback-platform-inference-handler \
      --region     us-east-1
"""

import boto3
import json
import argparse
from datetime import datetime, timezone


def update_lambda_env(function_name: str, hf_repo: str, region: str):
    """Update the MODEL_REPO env var in the Inference Lambda to point at the new HF model."""
    client = boto3.client("lambda", region_name=region)

    # Fetch current config so we don't overwrite other env vars
    current = client.get_function_configuration(FunctionName=function_name)
    env_vars = current.get("Environment", {}).get("Variables", {})

    # Switch to HF Inference API endpoint pattern
    env_vars["HF_MODEL_REPO"]  = hf_repo
    env_vars["INFERENCE_MODE"] = "huggingface_hub"  # signals app.py to use HF API

    client.update_function_configuration(
        FunctionName=function_name,
        Environment={"Variables": env_vars},
    )
    print(f"✅ Lambda '{function_name}' updated → HF model: {hf_repo}")


def record_deployment(bucket: str, hf_repo: str, region: str):
    """Write a deployment record to S3 for audit trail and rollback capability."""
    s3 = boto3.client("s3", region_name=region)
    timestamp = datetime.now(timezone.utc).isoformat()

    record = {
        "deployed_at":  timestamp,
        "hf_model_repo": hf_repo,
        "deployed_by":  "deploy_model.py",
        "status":       "active",
    }

    key = f"deployments/{timestamp[:10]}/{timestamp}.json"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(record, indent=2),
        ContentType="application/json",
    )
    print(f"📋 Deployment recorded → s3://{bucket}/{key}")


def main():
    parser = argparse.ArgumentParser(description="Deploy fine-tuned model to Lambda")
    parser.add_argument("--hf-repo",   required=True, help="Hugging Face model repo (e.g. username/model)")
    parser.add_argument("--bucket",    required=True, help="S3 Data Lake bucket name")
    parser.add_argument("--function",  required=True, help="Lambda function name to update")
    parser.add_argument("--region",    default="us-east-1", help="AWS region")
    args = parser.parse_args()

    print(f"\n🚀 Deploying model: {args.hf_repo}")
    update_lambda_env(args.function, args.hf_repo, args.region)
    record_deployment(args.bucket, args.hf_repo, args.region)
    print("\n🎉 Deployment complete! Your API is now serving the improved model.")


if __name__ == "__main__":
    main()
