variable "bucket_name" {
  description = "Globally unique name of the private process-knowledge bucket."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "bucket_name must be a valid 3-63 character lowercase S3 bucket name."
  }
}

variable "force_destroy" {
  description = "Whether Terraform may delete the bucket and all contained object versions during destroy."
  type        = bool
  default     = false
}

variable "versioning_enabled" {
  description = "Whether S3 object versioning is enabled for process-knowledge documents."
  type        = bool
  default     = false
}

variable "documents_prefix" {
  description = "S3 key prefix containing documents that the managed connector ingests."
  type        = string
  default     = "documents/"

  validation {
    condition = (
      length(var.documents_prefix) > 1 &&
      endswith(var.documents_prefix, "/") &&
      !startswith(var.documents_prefix, "/")
    )
    error_message = "documents_prefix must be relative, non-empty, and end with a slash."
  }
}

variable "tags" {
  description = "Tags to apply to the S3 bucket."
  type        = map(string)
  default     = {}
}
