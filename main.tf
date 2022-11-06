###################### AWS CUSTOM CONFIG RULE ######################
resource "aws_config_config_rule" "sqs_encryption_rule" {

  name             = "sqs-kms-encrypted"
  description      = "Checks that your Amazon sqs queue has server encryption enabled"
  input_parameters = "{\"KmsKeyId\": \"alias/aws/sqs\"}"
  scope {
    compliance_resource_types = ["AWS::SQS::Queue"]
  }

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = aws_lambda_function.compliance_evaluator.arn
    source_detail {
      message_type = "ConfigurationItemChangeNotification"
    }
    source_detail {
      message_type = "OversizedConfigurationItemChangeNotification"
    }
  }
}

###################### CONFIG RULE LAMBDA PERMISSION ######################
resource "aws_lambda_permission" "example" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.compliance_evaluator.arn
  principal     = "config.amazonaws.com"
  statement_id  = "AllowExecutionFromConfig"
}

###################### FALLBACK_EMAIL_ADDRESS ######################
resource "aws_ses_email_identity" "email_id" {
  email = var.default_email_id
}

