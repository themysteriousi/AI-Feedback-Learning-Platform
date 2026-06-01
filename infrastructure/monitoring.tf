##############################################
# CloudWatch Metric Alarms for the Platform
##############################################

# Alarm: Inference Lambda errors spike
resource "aws_cloudwatch_metric_alarm" "inference_errors" {
  alarm_name          = "${var.project_name}-inference-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Inference Lambda is throwing too many errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.inference_lambda.function_name
  }
}

# Alarm: Inference Lambda p99 latency too high
resource "aws_cloudwatch_metric_alarm" "inference_latency" {
  alarm_name          = "${var.project_name}-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  extended_statistic  = "p99"
  threshold           = 25000 # 25 seconds — Bedrock calls can be slow
  alarm_description   = "P99 inference latency exceeds 25s"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.inference_lambda.function_name
  }
}

# Alarm: DLQ receives messages (PII pipeline failures)
resource "aws_cloudwatch_metric_alarm" "pii_dlq_messages" {
  alarm_name          = "${var.project_name}-pii-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "NumberOfMessagesSent"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "PII Redaction pipeline has failed records in the DLQ"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.pii_dlq.name
  }
}

##############################################
# Custom Metrics Log Group (for platform metrics)
##############################################
resource "aws_cloudwatch_log_group" "platform_logs" {
  name              = "/ai-feedback-platform/metrics"
  retention_in_days = 30 # Keep logs for 30 days (free tier: 5GB/month)
}

##############################################
# AWS Budget Alarm — Stay Free!
##############################################
resource "aws_budgets_budget" "platform_budget" {
  name         = "${var.project_name}-monthly-budget"
  budget_type  = "COST"
  limit_amount = "2"   # Alert if monthly spend exceeds $2
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80 # Alert at 80% of budget ($1.60)
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100 # Alert when budget is exceeded
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}

##############################################
# Outputs
##############################################
output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.platform_logs.name
}
