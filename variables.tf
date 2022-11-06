############ Input variable definitions ############
variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-west-1"
}

variable "default_email_id" {
  description = "Email used to send & receive compliance messages if no resource tag email exists"
  type        = string
}

variable "send_compliance_email" {
  description = "Set to True if Compliance Emails should be sent"
  type        = bool
  default     = true
}

variable "lambda_function_name" {
  description = "Name of lambda function"
  type        = string
  default     = "sqs-compliance-evaluator"
}
