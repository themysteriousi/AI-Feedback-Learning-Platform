##############################################
# DynamoDB Table: Feedback Store
##############################################
resource "aws_dynamodb_table" "feedback_store" {
  name         = "${var.project_name}-feedback-store"
  billing_mode = "PAY_PER_REQUEST" # FREE tier friendly - no provisioned capacity costs
  hash_key     = "session_id"
  range_key    = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  # Enable DynamoDB Streams to trigger the PII Redaction Lambda
  stream_enabled   = true
  stream_view_type = "NEW_IMAGE" # Only send new/updated items downstream

  # Point-in-time recovery for data safety (free)
  point_in_time_recovery {
    enabled = true
  }

  # Server-side encryption (free with AWS owned keys)
  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "AI Feedback Store"
  }
}

##############################################
# S3 Data Lake: Cleaned Feedback Storage
##############################################
resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.project_name}-data-lake-${data.aws_caller_identity.current.account_id}"
}

# Block all public access to the data lake
resource "aws_s3_bucket_public_access_block" "data_lake_access_block" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable server-side encryption for all objects
resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake_encryption" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy: Move old data to Glacier after 90 days for cost savings
resource "aws_s3_bucket_lifecycle_configuration" "data_lake_lifecycle" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "archive-old-feedback"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Data source to get the current AWS account ID for unique bucket name
data "aws_caller_identity" "current" {}

##############################################
# Outputs
##############################################
output "dynamodb_table_name" {
  description = "Name of the DynamoDB feedback table"
  value       = aws_dynamodb_table.feedback_store.name
}

output "data_lake_bucket_name" {
  description = "Name of the S3 Data Lake bucket"
  value       = aws_s3_bucket.data_lake.id
}

output "dynamodb_stream_arn" {
  description = "ARN of the DynamoDB Stream"
  value       = aws_dynamodb_table.feedback_store.stream_arn
}
