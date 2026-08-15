module "budget" {
  source = "../../modules/budget"

  name        = "${local.name_prefix}-monthly-cost"
  limit_usd   = var.budget_limit_usd
  alert_email = var.budget_alert_email
  tags        = local.common_tags
}

module "case_table" {
  source = "../../modules/case_table"

  name                           = "${local.name_prefix}-cases"
  point_in_time_recovery_enabled = var.case_table_point_in_time_recovery_enabled
  tags                           = local.common_tags
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

module "case_documents" {
  source = "../../modules/case_documents"

  bucket_name                        = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-case-documents"
  force_destroy                      = var.case_documents_force_destroy
  versioning_enabled                 = var.case_documents_versioning_enabled
  temporary_document_expiration_days = var.temporary_document_expiration_days
  cors_allowed_origins               = var.case_documents_cors_allowed_origins
  tags                               = local.common_tags
}

module "knowledge_documents" {
  source = "../../modules/knowledge_documents"

  bucket_name        = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-knowledge"
  force_destroy      = var.knowledge_documents_force_destroy
  versioning_enabled = var.knowledge_documents_versioning_enabled
  documents_prefix   = var.knowledge_documents_prefix
  tags               = local.common_tags
}

module "managed_knowledge_base" {
  source = "../../modules/managed_knowledge_base"

  name             = "${local.name_prefix}-process-knowledge"
  aws_account_id   = data.aws_caller_identity.current.account_id
  aws_region       = var.aws_region
  bucket_arn       = module.knowledge_documents.arn
  bucket_name      = module.knowledge_documents.name
  documents_prefix = module.knowledge_documents.documents_prefix
  tags             = local.common_tags
}

module "agentcore_runtime" {
  count  = var.enable_agentcore_runtime ? 1 : 0
  source = "../../modules/agentcore_runtime"

  name                    = local.agentcore_runtime_name
  aws_account_id          = data.aws_caller_identity.current.account_id
  aws_region              = var.aws_region
  deployment_bucket_name  = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-agentcore-code"
  deployment_package_path = abspath("${path.root}/${var.agentcore_deployment_package_path}")
  case_table_arn          = module.case_table.arn
  case_table_name         = module.case_table.name
  knowledge_base_arn      = module.managed_knowledge_base.knowledge_base_arn
  knowledge_base_id       = module.managed_knowledge_base.knowledge_base_id
  bedrock_model_id        = var.agentcore_bedrock_model_id

  force_destroy_deployment_bucket = var.agentcore_deployment_bucket_force_destroy
  idle_runtime_session_timeout    = var.agentcore_idle_runtime_session_timeout
  max_lifetime                    = var.agentcore_max_lifetime
  tags                            = local.common_tags
}

data "aws_iam_policy_document" "transaction_search" {
  count = var.enable_agentcore_transaction_search ? 1 : 0

  statement {
    sid     = "TransactionSearchXRayAccess"
    effect  = "Allow"
    actions = ["logs:PutLogEvents"]
    resources = [
      "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:aws/spans:*",
      "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/application-signals/data:*",
    ]

    principals {
      type        = "Service"
      identifiers = ["xray.amazonaws.com"]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values = [
        "arn:${data.aws_partition.current.partition}:xray:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "transaction_search" {
  count = var.enable_agentcore_transaction_search ? 1 : 0

  policy_name     = "${local.name_prefix}-transaction-search"
  policy_document = data.aws_iam_policy_document.transaction_search[0].json
}

resource "aws_xray_trace_segment_destination" "transaction_search" {
  count = var.enable_agentcore_transaction_search ? 1 : 0

  destination = "CloudWatchLogs"

  depends_on = [aws_cloudwatch_log_resource_policy.transaction_search]
}

resource "aws_xray_indexing_rule" "transaction_search" {
  count = var.enable_agentcore_transaction_search ? 1 : 0

  name = "Default"

  rule {
    probabilistic {
      desired_sampling_percentage = var.agentcore_trace_indexing_percentage
    }
  }

  depends_on = [aws_xray_trace_segment_destination.transaction_search]
}
