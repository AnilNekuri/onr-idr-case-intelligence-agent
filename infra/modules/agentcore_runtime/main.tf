data "aws_partition" "current" {}

resource "aws_s3_bucket" "deployment" {
  bucket        = var.deployment_bucket_name
  force_destroy = var.force_destroy_deployment_bucket
  tags          = var.tags
}

resource "aws_s3_bucket_public_access_block" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_object" "deployment" {
  bucket      = aws_s3_bucket.deployment.id
  key         = "${var.name}/deployment_package.zip"
  source      = var.deployment_package_path
  etag        = var.use_source_hash ? null : filemd5(var.deployment_package_path)
  source_hash = var.use_source_hash ? filemd5(var.deployment_package_path) : null

  depends_on = [aws_s3_bucket_versioning.deployment]

  lifecycle {
    # Multipart S3 ETags are not MD5 hashes. New runtimes use source_hash;
    # ignoring the legacy ETag prevents unrelated runtime version churn.
    ignore_changes = [etag]
  }
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    sid     = "AssumeRolePolicy"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.aws_account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values = [
        "arn:${data.aws_partition.current.partition}:bedrock-agentcore:${var.aws_region}:${var.aws_account_id}:*"
      ]
    }
  }
}

resource "aws_iam_role" "runtime" {
  name               = "${var.name}-runtime-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = var.tags
}

data "aws_iam_policy_document" "runtime" {
  statement {
    sid       = "ReadDeploymentArtifact"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = [aws_s3_object.deployment.arn]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [var.aws_account_id]
    }
  }

  statement {
    sid    = "ReadAuthoritativeCase"
    effect = "Allow"
    actions = var.allow_case_writes ? [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
    ] : ["dynamodb:GetItem"]
    resources = [var.case_table_arn]
  }

  dynamic "statement" {
    for_each = var.claim_intake_table_arn == null ? [] : [var.claim_intake_table_arn]

    content {
      sid       = "PersistClaimIntakeSession"
      effect    = "Allow"
      actions   = ["dynamodb:GetItem", "dynamodb:PutItem"]
      resources = [statement.value]
    }
  }

  dynamic "statement" {
    for_each = var.case_documents_bucket_arn == null ? [] : [var.case_documents_bucket_arn]

    content {
      sid       = "ReadTemporaryClaimDocuments"
      effect    = "Allow"
      actions   = ["s3:GetObject"]
      resources = ["${statement.value}/temporary/*"]
    }
  }

  dynamic "statement" {
    for_each = var.enable_textract ? [1] : []

    content {
      sid    = "AnalyzeClaimDocuments"
      effect = "Allow"
      actions = [
        "textract:GetDocumentAnalysis",
        "textract:StartDocumentAnalysis",
      ]
      resources = ["*"]
    }
  }

  statement {
    sid       = "RetrieveProcessKnowledge"
    effect    = "Allow"
    actions   = ["bedrock:Retrieve"]
    resources = [var.knowledge_base_arn]
  }

  statement {
    sid    = "MantleInference"
    effect = "Allow"
    actions = [
      "bedrock-mantle:CreateInference",
      "bedrock-mantle:GetProject",
      "bedrock-mantle:ListProjects",
      "bedrock-mantle:ListTagsForResources",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DescribeAndCreateRuntimeLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:DescribeLogStreams",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
    ]
  }

  statement {
    sid     = "DescribeLogGroups"
    effect  = "Allow"
    actions = ["logs:DescribeLogGroups"]
    resources = [
      "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${var.aws_account_id}:log-group:*"
    ]
  }

  statement {
    sid    = "WriteRuntimeLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
    ]
  }

  statement {
    sid       = "ManageRuntimeLogDelivery"
    effect    = "Allow"
    actions   = ["logs:PutResourcePolicy"]
    resources = ["*"]
  }

  statement {
    sid    = "WriteRuntimeTraces"
    effect = "Allow"
    actions = [
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets",
      "xray:PutTelemetryRecords",
      "xray:PutTraceSegments",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "WriteRuntimeMetrics"
    effect    = "Allow"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["bedrock-agentcore"]
    }
  }
}

resource "aws_iam_role_policy" "runtime" {
  name   = "${var.name}-runtime-policy"
  role   = aws_iam_role.runtime.id
  policy = data.aws_iam_policy_document.runtime.json
}

resource "aws_bedrockagentcore_agent_runtime" "this" {
  agent_runtime_name = var.name
  description        = var.runtime_description
  role_arn           = aws_iam_role.runtime.arn
  tags               = var.tags

  agent_runtime_artifact {
    code_configuration {
      entry_point = ["opentelemetry-instrument", var.entry_point]
      runtime     = "PYTHON_3_13"

      code {
        s3 {
          bucket     = aws_s3_object.deployment.bucket
          prefix     = aws_s3_object.deployment.key
          version_id = aws_s3_object.deployment.version_id
        }
      }
    }
  }

  environment_variables = merge(
    {
      AWS_REGION                = var.aws_region
      BEDROCK_KNOWLEDGE_BASE_ID = var.knowledge_base_id
      BEDROCK_MODEL_ID          = var.bedrock_model_id
      CASE_REPOSITORY           = "dynamodb"
      DYNAMODB_CASE_TABLE       = var.case_table_name
      OTEL_PYTHON_DISTRO        = "aws_distro"
      OTEL_PYTHON_CONFIGURATOR  = "aws_configurator"
    },
    var.claim_intake_table_name == null ? {} : {
      CLAIM_INTAKE_TABLE = var.claim_intake_table_name
    },
    var.case_documents_bucket_name == null ? {} : {
      S3_CASE_DOCUMENTS_BUCKET = var.case_documents_bucket_name
    },
    var.additional_environment_variables,
  )

  lifecycle_configuration {
    idle_runtime_session_timeout = var.idle_runtime_session_timeout
    max_lifetime                 = var.max_lifetime
  }

  network_configuration {
    network_mode = "PUBLIC"
  }

  protocol_configuration {
    server_protocol = "HTTP"
  }

  depends_on = [aws_iam_role_policy.runtime]
}

resource "aws_bedrockagentcore_agent_runtime_endpoint" "this" {
  agent_runtime_id      = aws_bedrockagentcore_agent_runtime.this.agent_runtime_id
  agent_runtime_version = aws_bedrockagentcore_agent_runtime.this.agent_runtime_version
  name                  = var.endpoint_name
  description           = var.endpoint_description
  tags                  = var.tags
}
