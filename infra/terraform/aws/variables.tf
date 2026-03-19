variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "af-south-1"
}

variable "bucket_name" {
  type        = string
  description = "Unique S3 bucket name for statement documents"
}

variable "tags" {
  type        = map(string)
  description = "Tags for all resources"
  default = {
    project = "secure-file-statement-delivery"
  }
}
