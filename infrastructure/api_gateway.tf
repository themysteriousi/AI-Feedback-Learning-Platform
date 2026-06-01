# Create an HTTP API Gateway
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type"]
    max_age       = 300
  }
}

# Integration between API Gateway and the Inference Lambda
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"
  
  connection_type        = "INTERNET"
  description            = "Lambda integration for AI Inference"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.inference_lambda.invoke_arn
  payload_format_version = "2.0"
}

# Route for the POST /generate endpoint
resource "aws_apigatewayv2_route" "post_generate_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /generate"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Default stage with auto-deploy
resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

# Permission for API Gateway to invoke the Lambda function
resource "aws_lambda_permission" "api_gw_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.inference_lambda.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# Output the API URL for the frontend
output "api_url" {
  description = "The base URL of the HTTP API Gateway"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}
