# ---------------------------------------------------------------------------
# ECR repository
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "backend" {
  name                 = "hexagone-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 100 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 100
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# ---------------------------------------------------------------------------
# S3 uploads bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "uploads" {
  bucket = "hexagone-uploads"
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "GET"]
    allowed_origins = ["https://${var.domain_name}"]
    max_age_seconds = 3600
  }
}

# ---------------------------------------------------------------------------
# IAM role for Lambda execution
# ---------------------------------------------------------------------------

resource "aws_iam_role" "lambda_exec" {
  name = "HexagoneLambdaExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_logging" {
  name = "HexagoneLambdaLogging"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "arn:aws:logs:${data.aws_region.current.name}:*:*"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_vpc_execution" {
  name = "HexagoneLambdaVPCExecution"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DeleteNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*",
        Condition = {
          ArnLikeIfExists = {
            "ec2:Vpc" : aws_vpc.main.arn
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_s3_uploads" {
  name = "HexagoneLambdaS3Uploads"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject"
      ]
      Resource = "${aws_s3_bucket.uploads.arn}/*"
    }]
  })
}

# ---------------------------------------------------------------------------
# CloudWatch log groups
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/hexagone-backend"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/hexagone-backend"
  retention_in_days = 7
}

# ---------------------------------------------------------------------------
# Lambda function
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "backend" {
  function_name = "hexagone-backend"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.backend.repository_url}:${var.lambda_image_tag}"
  architectures = ["arm64"]
  timeout       = 30
  memory_size   = 512

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENV                = "PROD"
      DATABASE_URL       = local.DATABASE_URL
      HEXAGONE_S3_BUCKET = aws_s3_bucket.uploads.id
    }
  }
}

# ---------------------------------------------------------------------------
# API Gateway HTTP API v2
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_api" "backend" {
  name          = "hexagone-backend"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.backend.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.backend.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.backend.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.backend.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      ip               = "$context.identity.sourceIp"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      protocol         = "$context.protocol"
      responseLength   = "$context.responseLength"
      errorMessage     = "$context.error.message"
      integrationError = "$context.integrationErrorMessage"
    })
  }
}

# ---------------------------------------------------------------------------
# Lambda permission for API Gateway invocation
# ---------------------------------------------------------------------------

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.backend.execution_arn}/*/*"
}

# ---------------------------------------------------------------------------
# DB Ops Lambda function
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "lambda_db_ops" {
  name              = "/aws/lambda/hexagone-db-ops"
  retention_in_days = 7
}

resource "aws_lambda_function" "db_ops" {
  function_name = "hexagone-db-ops"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.backend.repository_url}:${var.lambda_image_tag}"
  architectures = ["arm64"]
  timeout       = 300 # 5 minutes for database operations
  memory_size   = 512

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENV          = "PROD"
      DATABASE_URL = local.DATABASE_URL
    }
  }

  # Override the CMD to use the database operations handler
  image_config {
    command = ["src.app.handlers.db.handler"]
  }
}

# ---------------------------------------------------------------------------
# Upload Processing Lambda function
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "lambda_upload_processor" {
  name              = "/aws/lambda/hexagone-upload-processor"
  retention_in_days = 7
}

resource "aws_lambda_function" "upload_processor" {
  function_name = "hexagone-upload-processor"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.backend.repository_url}:${var.lambda_image_tag}"
  architectures = ["arm64"]
  timeout       = 60
  memory_size   = 512

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENV                = "PROD"
      DATABASE_URL       = local.DATABASE_URL
      HEXAGONE_S3_BUCKET = aws_s3_bucket.uploads.id
    }
  }

  image_config {
    command = ["src.app.handlers.file_upload.handler"]
  }
}

# ---------------------------------------------------------------------------
# S3 → Lambda event notification
# ---------------------------------------------------------------------------

resource "aws_lambda_permission" "s3_invoke_upload_processor" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.uploads.arn
}

resource "aws_s3_bucket_notification" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.upload_processor.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.s3_invoke_upload_processor]
}
