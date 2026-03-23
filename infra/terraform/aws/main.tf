provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnet_ids" "default" {
  vpc_id = data.aws_vpc.default.id
}

locals {
  common_tags = merge(var.tags, { environment = var.environment })
}

resource "aws_s3_bucket" "statements" {
  bucket = var.bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "statements" {
  bucket = aws_s3_bucket.statements.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "statements" {
  bucket = aws_s3_bucket.statements.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "statements" {
  bucket = aws_s3_bucket.statements.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_ecr_repository" "api" {
  name                 = format("%s-%s", var.repository_name, var.environment)
  image_tag_mutability = "MUTABLE"
  tags                 = local.common_tags
}

resource "aws_security_group" "alb" {
  name        = format("alb-%s", var.environment)
  description = "HTTP listener for the API"
  vpc_id      = data.aws_vpc.default.id
  tags        = local.common_tags

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs" {
  name        = format("ecs-%s", var.environment)
  description = "ECS tasks for the API"
  vpc_id      = data.aws_vpc.default.id
  tags        = local.common_tags

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name        = format("db-%s", var.environment)
  description = "PostgreSQL access"
  vpc_id      = data.aws_vpc.default.id
  tags        = local.common_tags

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "redis" {
  name        = format("redis-%s", var.environment)
  description = "Redis access for ECS"
  vpc_id      = data.aws_vpc.default.id
  tags        = local.common_tags

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "api" {
  name               = format("alb-%s", var.environment)
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnet_ids.default.ids
  idle_timeout       = 60
  tags               = local.common_tags
}

resource "aws_lb_target_group" "api" {
  name        = format("tg-%s-api", var.environment)
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    path                = "/"
    matcher             = "200-399"
    interval            = 30
    timeout             = 10
    healthy_threshold   = 2
    unhealthy_threshold = 5
  }

  tags = local.common_tags
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = format("/ecs/%s/api", var.environment)
  retention_in_days = 14
  tags              = local.common_tags
}

resource "aws_ecs_cluster" "main" {
  name = format("ecs-%s", var.environment)
  tags = local.common_tags
}

data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = format("ecs-execution-%s", var.environment)
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name               = format("ecs-task-%s", var.environment)
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
  tags               = local.common_tags
}

resource "aws_secretsmanager_secret" "statement_api_key" {
  name = format("%s-statement-api-key", var.environment)
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "statement_api_key" {
  secret_id     = aws_secretsmanager_secret.statement_api_key.id
  secret_string = var.statement_api_key
}

resource "aws_secretsmanager_secret" "db_password" {
  name = format("%s-db-password", var.environment)
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

resource "aws_secretsmanager_secret" "redis_password" {
  name = format("%s-redis-password", var.environment)
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "redis_password" {
  secret_id     = aws_secretsmanager_secret.redis_password.id
  secret_string = var.redis_password
}

data "aws_iam_policy_document" "ecs_task_role" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.statements.arn,
      format("%s/*", aws_s3_bucket.statements.arn)
    ]
  }

  statement {
    effect = "Allow"
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.statement_api_key.arn,
      aws_secretsmanager_secret.db_password.arn,
      aws_secretsmanager_secret.redis_password.arn
    ]
  }
}

resource "aws_iam_role_policy" "ecs_task_role" {
  name   = format("ecs-task-policy-%s", var.environment)
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_role.json
}

resource "aws_db_subnet_group" "main" {
  name       = format("db-subnet-%s", var.environment)
  subnet_ids = data.aws_subnet_ids.default.ids
  tags       = local.common_tags
}

resource "aws_db_instance" "main" {
  identifier                 = format("db-%s", var.environment)
  allocated_storage          = var.postgres_storage_gb
  engine                     = "postgres"
  engine_version             = var.postgres_version
  instance_class             = var.postgres_instance_class
  name                       = var.database_name
  username                   = var.postgres_admin_username
  password                   = var.db_password
  db_subnet_group_name       = aws_db_subnet_group.main.name
  vpc_security_group_ids     = [aws_security_group.db.id]
  skip_final_snapshot        = true
  publicly_accessible        = false
  storage_encrypted          = true
  storage_type               = "gp3"
  backup_retention_period    = 7
  auto_minor_version_upgrade = true
  multi_az                   = false
  parameter_group_name       = "default.postgres16"
  port                       = 5432
  tags                       = local.common_tags
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = format("redis-subnet-%s", var.environment)
  subnet_ids = data.aws_subnet_ids.default.ids
  tags       = local.common_tags
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = format("redis-%s", var.environment)
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  num_cache_nodes      = var.redis_num_cache_nodes
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
  port                 = 6379
  auth_token           = var.redis_password
  transit_encryption_enabled = false
  snapshot_retention_limit   = 0
  apply_immediately          = true
  auto_minor_version_upgrade = true
  tags                       = local.common_tags
}

resource "aws_ecs_task_definition" "api" {
  family                   = format("ecs-task-%s", var.environment)
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  tags                     = local.common_tags

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = var.app_image != "" ? var.app_image : format("%s:%s", aws_ecr_repository.api.repository_url, var.app_image_tag)
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
      environment = [
        { name = "FASTAPI_ENV", value = var.environment },
        { name = "DEBUG", value = "false" },
        { name = "LOG_LEVEL", value = var.log_level },
        { name = "DATABASE_HOST", value = aws_db_instance.main.address },
        { name = "DATABASE_PORT", value = "5432" },
        { name = "DATABASE_NAME", value = var.database_name },
        { name = "DATABASE_USERNAME", value = var.postgres_admin_username },
        { name = "DATABASE_SSL_MODE", value = "require" },
        { name = "CACHE_HOST", value = aws_elasticache_cluster.redis.cache_nodes[0].address },
        { name = "CACHE_PORT", value = "6379" },
        { name = "CACHE_DB", value = "0" },
        { name = "CACHE_USE_SSL", value = "false" },
        { name = "CACHE_SSL_CERT_REQS", value = "none" },
        { name = "STORAGE_PROVIDER", value = "aws" },
        { name = "STORAGE_BUCKET_NAME", value = aws_s3_bucket.statements.bucket },
        { name = "PDF_PASSWORD_KDF_ITERATIONS", value = tostring(var.pdf_password_kdf_iterations) }
      ]
      secrets = [
        {
          name      = "DATABASE_PASSWORD"
          valueFrom = aws_secretsmanager_secret.db_password.arn
        },
        {
          name      = "CACHE_PASSWORD"
          valueFrom = aws_secretsmanager_secret.redis_password.arn
        },
        {
          name      = "STATEMENT_API_KEY"
          valueFrom = aws_secretsmanager_secret.statement_api_key.arn
        }
      ]
    }
  ])
}

resource "aws_ecs_service" "api" {
  name            = format("ecs-svc-%s", var.environment)
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  platform_version = "1.4.0"
  tags            = local.common_tags

  network_configuration {
    subnets         = data.aws_subnet_ids.default.ids
    security_groups = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60

  depends_on = [aws_lb_listener.http]
}