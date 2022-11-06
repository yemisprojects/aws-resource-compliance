######################## LAMBDA FUNCTION ########################
resource "aws_lambda_function" "compliance_evaluator" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_exec_role.arn

  s3_bucket        = aws_s3_bucket.lambda_bucket.id
  s3_key           = aws_s3_object.lambda_package.key
  source_code_hash = data.archive_file.lambda_eval_compliance.output_base64sha256

  runtime     = "python3.9"
  handler     = "main_lambda.lambda_handler"
  timeout     = 300
  memory_size = 128

  environment {
    variables = {
      LOG_LEVEL      = "INFO"
      SEND_EMAIL     = var.send_compliance_email
      FALLBACK_EMAIL = var.default_email_id
    }
  }
}

######################## LAMBDA LOG GROUP ########################
resource "aws_cloudwatch_log_group" "lambda_log_grp" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 30
}

######################## LAMBDA S3 BUCKET ########################
resource "random_pet" "lambda_bucket_name" {
  prefix = "lambda-eval-compliance"
}

resource "aws_s3_bucket" "lambda_bucket" {
  bucket        = random_pet.lambda_bucket_name.id
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.lambda_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_bkt_encryptn" {
  bucket = aws_s3_bucket.lambda_bucket.bucket
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

##################### LAMBDA DEPLOYMENT PACKAGE #####################
data "archive_file" "lambda_eval_compliance" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/src"
  output_path = "${path.module}/lambda/lambda_package.zip"
}

resource "aws_s3_object" "lambda_package" {
  bucket = aws_s3_bucket.lambda_bucket.id
  key    = "lambda_package.zip"
  source = data.archive_file.lambda_eval_compliance.output_path
  etag   = filemd5(data.archive_file.lambda_eval_compliance.output_path)
}
