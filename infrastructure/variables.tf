variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ai-feedback-platform"
}

variable "alert_email" {
  description = "Email address to send CloudWatch and Budget alerts to"
  type        = string
  default     = "your-email@example.com" # Change this before deploying
}
