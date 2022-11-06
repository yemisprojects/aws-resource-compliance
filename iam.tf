locals {
  account_id = data.aws_caller_identity.caller_id.account_id
}

########################### STS ###########################
data "aws_caller_identity" "caller_id" {}

######################## LAMBDA ROLE ########################
resource "aws_iam_role" "lambda_exec_role" {
  name               = "lambda-compliance-evaluator"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
  inline_policy {
    name   = "LambdaFunctionPermissions"
    policy = data.aws_iam_policy_document.lambda_inline_policy.json
  }
}

################## LAMBDA ROLE ROLETRUST POLICY ##################
data "aws_iam_policy_document" "lambda_assume_role_policy" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

######### LAMBDA POLICY #########
data "aws_iam_policy_document" "lambda_inline_policy" {
  statement {
    sid       = "AllowConfigRuleUpdate"
    effect    = "Allow"
    actions   = ["config:PutEvaluations"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowLambdaCreateLogGroup"
    effect = "Allow"
    actions = ["sqs:GetQueueAttributes", "sqs:SetQueueAttributes",
    "sqs:ListQueueTags", "logs:CreateLogGroup", "ses:SendEmail"]
    resources = ["arn:aws:logs:${var.aws_region}:*:log-group:*",
      "arn:aws:sqs:${var.aws_region}:${local.account_id}:*",
    "arn:aws:ses:${var.aws_region}:${local.account_id}:identity/*"]
  }

  statement {
    sid       = "AllowLambdaCreateLogStreamsAndWriteEventLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.lambda_log_grp.arn}:*"]
  }
}

