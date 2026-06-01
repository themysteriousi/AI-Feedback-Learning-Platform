##############################################
# IAM Role for PII Redaction Lambda
##############################################
resource "aws_iam_role" "pii_lambda_role" {
  name = "${var.project_name}-pii-redaction-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "pii_lambda_basic" {
  role       = aws_iam_role.pii_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Allow Lambda to read from DynamoDB Streams
resource "aws_iam_policy" "pii_dynamodb_stream_policy" {
  name = "${var.project_name}-pii-dynamodb-stream-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:DescribeStream",
        "dynamodb:ListStreams"
      ]
      Resource = aws_dynamodb_table.feedback_store.stream_arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "pii_dynamodb_attachment" {
  role       = aws_iam_role.pii_lambda_role.name
  policy_arn = aws_iam_policy.pii_dynamodb_stream_policy.arn
}

# Allow Lambda to write cleaned records to S3 Data Lake
resource "aws_iam_policy" "pii_s3_write_policy" {
  name = "${var.project_name}-pii-s3-write-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject"]
      Resource = "${aws_s3_bucket.data_lake.arn}/feedback/*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "pii_s3_attachment" {
  role       = aws_iam_role.pii_lambda_role.name
  policy_arn = aws_iam_policy.pii_s3_write_policy.arn
}

##############################################
# Lambda Layer: Presidio Dependencies
##############################################
# NOTE: You must first build the Presidio layer locally:
#   cd src/pii_redaction && pip install -r requirements.txt -t layer/python && cd ../..
#   zip -r build/presidio_layer.zip src/pii_redaction/layer/
resource "aws_lambda_layer_version" "presidio_layer" {
  filename            = "${path.module}/../build/presidio_layer.zip"
  layer_name          = "${var.project_name}-presidio-layer"
  compatible_runtimes = ["python3.11"]
  description         = "Microsoft Presidio for open-source PII redaction"
}

##############################################
# PII Redaction Lambda Function
##############################################
data "archive_file" "pii_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/pii_redaction"
  output_path = "${path.module}/../build/pii_redaction_lambda.zip"
  excludes    = ["requirements.txt", "layer"]
}

resource "aws_lambda_function" "pii_redaction_lambda" {
  filename         = data.archive_file.pii_lambda_zip.output_path
  function_name    = "${var.project_name}-pii-redaction"
  role             = aws_iam_role.pii_lambda_role.arn
  handler          = "app.lambda_handler"
  source_code_hash = data.archive_file.pii_lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 60  # Presidio NLP can take a moment
  memory_size      = 512 # Presidio needs more memory than a typical Lambda

  layers = [aws_lambda_layer_version.presidio_layer.arn]

  environment {
    variables = {
      DATA_LAKE_BUCKET = aws_s3_bucket.data_lake.id
      DATA_LAKE_PREFIX = "feedback/raw/"
    }
  }
}

##############################################
# Event Source Mapping: DynamoDB Stream → Lambda
##############################################
resource "aws_lambda_event_source_mapping" "dynamodb_to_pii_lambda" {
  event_source_arn  = aws_dynamodb_table.feedback_store.stream_arn
  function_name     = aws_lambda_function.pii_redaction_lambda.arn
  starting_position = "LATEST" # Only process new records, not historical ones

  # Batch settings: process up to 10 records at once, wait max 5s for a batch
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5

  # On failure, skip poisonous records rather than blocking the whole stream
  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.pii_dlq.arn
    }
  }
}

##############################################
# Dead Letter Queue for failed stream records
##############################################
resource "aws_sqs_queue" "pii_dlq" {
  name                      = "${var.project_name}-pii-dlq"
  message_retention_seconds = 1209600 # Keep failed messages for 14 days
}

# Grant the Lambda role permission to send to the DLQ
resource "aws_iam_policy" "pii_dlq_policy" {
  name = "${var.project_name}-pii-dlq-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:SendMessage"]
      Resource = aws_sqs_queue.pii_dlq.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "pii_dlq_attachment" {
  role       = aws_iam_role.pii_lambda_role.name
  policy_arn = aws_iam_policy.pii_dlq_policy.arn
}
