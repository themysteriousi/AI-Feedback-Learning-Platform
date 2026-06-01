##############################################
# Feedback Writer Lambda + API Gateway Route
##############################################

# IAM Role
resource "aws_iam_role" "feedback_writer_role" {
  name = "${var.project_name}-feedback-writer-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "feedback_writer_basic" {
  role       = aws_iam_role.feedback_writer_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Allow this Lambda to write to DynamoDB
resource "aws_iam_policy" "feedback_writer_dynamo_policy" {
  name = "${var.project_name}-feedback-writer-dynamo-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem"]
      Resource = aws_dynamodb_table.feedback_store.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "feedback_writer_dynamo_attachment" {
  role       = aws_iam_role.feedback_writer_role.name
  policy_arn = aws_iam_policy.feedback_writer_dynamo_policy.arn
}

# Lambda Function
data "archive_file" "feedback_writer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/feedback_writer"
  output_path = "${path.module}/../build/feedback_writer_lambda.zip"
}

resource "aws_lambda_function" "feedback_writer_lambda" {
  filename         = data.archive_file.feedback_writer_zip.output_path
  function_name    = "${var.project_name}-feedback-writer"
  role             = aws_iam_role.feedback_writer_role.arn
  handler          = "app.lambda_handler"
  source_code_hash = data.archive_file.feedback_writer_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      FEEDBACK_TABLE_NAME = aws_dynamodb_table.feedback_store.name
    }
  }
}

# API Gateway Integration
resource "aws_apigatewayv2_integration" "feedback_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.feedback_writer_lambda.invoke_arn
  payload_format_version = "2.0"
}

# Route: POST /feedback
resource "aws_apigatewayv2_route" "post_feedback_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /feedback"
  target    = "integrations/${aws_apigatewayv2_integration.feedback_integration.id}"
}

# Permission for API GW to invoke this Lambda
resource "aws_lambda_permission" "api_gw_feedback_permission" {
  statement_id  = "AllowFeedbackExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.feedback_writer_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
