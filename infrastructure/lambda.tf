# IAM Role for Inference Lambda
resource "aws_iam_role" "inference_lambda_role" {
  name = "${var.project_name}-inference-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach basic execution policy for CloudWatch logs
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.inference_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom policy to allow Bedrock model invocation
resource "aws_iam_policy" "bedrock_invoke_policy" {
  name        = "${var.project_name}-bedrock-invoke-policy"
  description = "Allow Lambda to invoke Bedrock models"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*" # Restrict this to specific models in production
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_bedrock_attachment" {
  role       = aws_iam_role.inference_lambda_role.name
  policy_arn = aws_iam_policy.bedrock_invoke_policy.arn
}

# Create a zip of the Lambda source code
data "archive_file" "inference_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/inference"
  output_path = "${path.module}/../build/inference_lambda.zip"
}

# Lambda Function definition
resource "aws_lambda_function" "inference_lambda" {
  filename         = data.archive_file.inference_lambda_zip.output_path
  function_name    = "${var.project_name}-inference-handler"
  role             = aws_iam_role.inference_lambda_role.arn
  handler          = "app.lambda_handler"
  source_code_hash = data.archive_file.inference_lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30 # Bedrock can take a few seconds
  memory_size      = 256

  environment {
    variables = {
      # You can change this to meta.llama3-8b-instruct-v1:0
      MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0" 
    }
  }
}
