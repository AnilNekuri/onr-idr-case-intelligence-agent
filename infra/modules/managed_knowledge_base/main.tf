data "aws_partition" "current" {}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.aws_account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "AWS:SourceArn"
      values = [
        "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}:${var.aws_account_id}:knowledge-base/*"
      ]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.name}-service-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = var.tags
}

data "aws_iam_policy_document" "s3_access" {
  statement {
    sid       = "ListKnowledgeDocuments"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.bucket_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = [var.documents_prefix, "${var.documents_prefix}*"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [var.aws_account_id]
    }
  }

  statement {
    sid       = "ReadKnowledgeDocuments"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${var.bucket_arn}/${var.documents_prefix}*"]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [var.aws_account_id]
    }
  }
}

resource "aws_iam_role_policy" "s3_access" {
  name   = "${var.name}-s3-read"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.s3_access.json
}

resource "aws_bedrockagent_knowledge_base" "this" {
  name        = var.name
  description = var.description
  role_arn    = aws_iam_role.this.arn
  tags        = var.tags

  knowledge_base_configuration {
    type = "MANAGED"

    managed_knowledge_base_configuration {
      embedding_model_type = "MANAGED"
    }
  }

  depends_on = [aws_iam_role_policy.s3_access]
}

data "aws_iam_policy_document" "retrieve" {
  statement {
    sid       = "RetrieveProcessKnowledge"
    effect    = "Allow"
    actions   = ["bedrock:Retrieve"]
    resources = [aws_bedrockagent_knowledge_base.this.arn]
  }
}

resource "aws_iam_policy" "retrieve" {
  name        = "${var.name}-retrieve"
  description = "Allows retrieval from the managed process-guidance Knowledge Base."
  policy      = data.aws_iam_policy_document.retrieve.json
  tags        = var.tags
}

resource "aws_bedrockagent_data_source" "s3" {
  name                 = "${var.name}-s3"
  description          = "Curated public process guidance from ${var.bucket_name}/${var.documents_prefix}."
  knowledge_base_id    = aws_bedrockagent_knowledge_base.this.id
  data_deletion_policy = "DELETE"

  data_source_configuration {
    type = "MANAGED_KNOWLEDGE_BASE_CONNECTOR"

    managed_knowledge_base_connector_configuration {
      connector_parameters = jsonencode({
        type    = "S3"
        version = "1"
        connectionConfiguration = {
          bucketName           = var.bucket_name
          bucketOwnerAccountId = var.aws_account_id
        }
        filterConfiguration = {
          inclusionPrefixes = [var.documents_prefix]
        }
      })
    }
  }
}
