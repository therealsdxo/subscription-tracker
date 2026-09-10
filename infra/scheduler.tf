# EventBridge Scheduler → run the daily subscription sweep as a one-off ECS task.

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

data "aws_iam_policy_document" "scheduler_run_task" {
  statement {
    actions   = ["ecs:RunTask"]
    resources = ["${aws_ecs_task_definition.job.arn_without_revision}:*"]
  }
  statement {
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.task_execution.arn, aws_iam_role.task.arn]
  }
}

resource "aws_iam_role_policy" "scheduler_run_task" {
  name   = "run-task"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler_run_task.json
}

resource "aws_ecs_task_definition" "job" {
  family                   = "${local.name}-job"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name        = "job"
      image       = local.image
      essential   = true
      environment = local.common_env
      secrets     = local.common_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "job"
        }
      }
    }
  ])
}

locals {
  job_targets = {
    "expiry-sweep" = {
      # 00:30 IST daily
      schedule = "cron(0 19 * * ? *)"
      command  = ["python", "-m", "scripts.run_expiry_job"]
    }
    "generate-deliveries" = {
      # 04:00 IST daily — pre-generate the next open day's list
      schedule = "cron(30 22 * * ? *)"
      command  = ["python", "-m", "scripts.generate_deliveries"]
    }
  }
}

resource "aws_scheduler_schedule" "job" {
  for_each = local.job_targets

  name                         = "${local.name}-${each.key}"
  schedule_expression          = each.value.schedule
  schedule_expression_timezone = "UTC"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.scheduler.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.job.arn_without_revision
      launch_type         = "FARGATE"
      task_count          = 1

      network_configuration {
        subnets          = aws_subnet.private[*].id
        security_groups  = [aws_security_group.ecs.id]
        assign_public_ip = false
      }
    }

    input = jsonencode({
      containerOverrides = [
        { name = "job", command = each.value.command }
      ]
    })
  }
}
