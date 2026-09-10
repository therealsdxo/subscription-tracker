# HealthX — Infrastructure (AWS, `ap-south-1`)

Terraform for the **backend** of HealthX: VPC, RDS PostgreSQL, ECR, an ECS
Fargate service behind an ALB, Secrets Manager, EventBridge Scheduler for the
daily jobs, and CloudWatch alarms.

> This is authored infra — reviewed and `terraform validate`-clean. It has **not
> been applied**. Frontend hosting (Amplify / S3+CloudFront) is out of scope
> until a frontend exists.

## What it provisions

| File | Resources |
|---|---|
| `network.tf` | VPC, 2 public + 2 private subnets, IGW, 1 NAT, route tables, security groups (ALB→ECS→RDS) |
| `database.tf` | RDS PostgreSQL 16 (private, `db.t4g.micro`), gp3 encrypted storage, automated backups + PITR, `timezone=UTC` parameter group, deletion protection, Multi-AZ toggle |
| `registry.tf` | ECR repo `healthx/api` + lifecycle policy (keep 20) |
| `secrets.tf` | Secrets Manager: `healthx-<env>/database-url`, `healthx-<env>/jwt-secret` (random) |
| `service.tf` | ECS cluster, log group, task roles, API + `migrate` task definitions, ALB + target group (health check `/api/v1/health`), HTTP/HTTPS listeners, service, CPU autoscaling (1–4) |
| `scheduler.tf` | `job` task definition + EventBridge schedules for `run_expiry_job` (00:30 IST) and `generate_deliveries` (04:00 IST) |
| `observability.tf` | SNS alarm topic + alarms: ALB 5xx, ALB p95 latency, RDS CPU / free storage / connections |

## Prerequisites

- Terraform ≥ 1.6, AWS credentials for the target account
- An S3 bucket + DynamoDB lock table for remote state (recommended)

## First apply

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars     # edit
# configure remote state, then:
terraform init -backend-config=backend.hcl        # or: terraform init -backend=false  (validate only)
terraform apply
```

`terraform apply` creates the ECR repo and the RDS instance. Then:

```bash
# 1. build + push the API image
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin "$(terraform output -raw ecr_repository_url | cut -d/ -f1)"
docker build -t "$(terraform output -raw ecr_repository_url):$(git rev-parse --short HEAD)" ../backend
docker push "$(terraform output -raw ecr_repository_url):$(git rev-parse --short HEAD)"

# 2. point Terraform at that tag and apply again (creates the ECS service)
terraform apply -var "api_image_tag=$(git rev-parse --short HEAD)"

# 3. run migrations (one-off task)
aws ecs run-task --cluster "$(terraform output -raw ecs_cluster)" \
  --task-definition "$(terraform output -raw migrate_task_definition)" \
  --launch-type FARGATE --network-configuration '...'   # private subnets + ECS SG

# 4. seed the first admin (one-off, similar run-task with command scripts.seed)
```

## Rolling a new version

1. Build + push a new image tag.
2. `aws ecs run-task … <migrate task>` — apply migrations.
3. `terraform apply -var api_image_tag=<tag>` — new task definition + rolling
   deploy (circuit breaker rolls back on failure).

## Environment variables

The task definitions inject:

| Var | Source |
|---|---|
| `HEALTHX_DATABASE_URL` | Secrets Manager `…/database-url` |
| `HEALTHX_JWT_SECRET` | Secrets Manager `…/jwt-secret` |
| `HEALTHX_ENV` / `HEALTHX_TIMEZONE` / `HEALTHX_CORS_ORIGINS` / `HEALTHX_LOG_LEVEL` | task env (from `var.*`) |

## Notes / follow-ups

- **Single NAT gateway** — not AZ-redundant, chosen for cost. Add a second for
  production resilience.
- **HTTPS** is created only when `domain_name` is set; otherwise the ALB serves
  plain HTTP and must sit behind a TLS-terminating layer. Validate the ACM cert
  with the DNS records in `terraform output acm_certificate_validation_records`.
- **Rate limiting** in the API is in-process; with `api_desired_count > 1` it is
  per-task. A shared store (ElastiCache Redis) is the fix — not provisioned here.
- **Frontend hosting** — add when the Next.js app lands (Amplify Hosting or
  S3 + CloudFront + a separate ALB rule).
