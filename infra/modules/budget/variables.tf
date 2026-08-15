variable "name" {
  description = "Unique name for the monthly AWS cost budget."
  type        = string

  validation {
    condition     = length(trimspace(var.name)) > 0
    error_message = "name must not be empty."
  }
}

variable "limit_usd" {
  description = "Monthly budget limit in US dollars."
  type        = number

  validation {
    condition     = var.limit_usd > 0
    error_message = "limit_usd must be greater than zero."
  }
}

variable "alert_email" {
  description = "Email address that receives actual and forecasted cost alerts. AWS may ask the recipient to confirm the subscription."
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must be a valid email address."
  }
}

variable "tags" {
  description = "Tags to apply to the budget in addition to provider default tags."
  type        = map(string)
  default     = {}
}
