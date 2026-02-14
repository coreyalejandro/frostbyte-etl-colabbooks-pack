# Frostbyte ETL Pipeline — Makefile
# Quick commands for development workflow

.PHONY: help start stop restart status logs build reset

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

start: ## Start all services (development mode)
	@./scripts/start-frostbyte.sh start

prod: ## Start all services (production mode with rebuild)
	@./scripts/start-frostbyte.sh prod

stop: ## Stop all services
	@./scripts/start-frostbyte.sh stop

restart: ## Restart all services
	@./scripts/start-frostbyte.sh restart

status: ## Show service status and health
	@./scripts/start-frostbyte.sh status

logs: ## Show logs for all services
	@./scripts/start-frostbyte.sh logs

logs-api: ## Show logs for pipeline API only
	@./scripts/start-frostbyte.sh logs pipeline-api

logs-dashboard: ## Show logs for admin dashboard only
	@./scripts/start-frostbyte.sh logs admin-dashboard

build: ## Build all Docker images
	@docker-compose build

reset: ## DANGER: Stop and destroy all data
	@./scripts/start-frostbyte.sh reset

check: ## Run connection diagnostics
	@./scripts/check-pipeline-connection.sh

dev: ## Start infrastructure only (run pipeline API locally for hot reload)
	@docker-compose up -d redis postgres minio qdrant
	@echo "Infrastructure started. Run pipeline API locally with:"
	@echo "  cd pipeline && uvicorn pipeline.main:app --reload --port 8000"

shell-api: ## Open shell in pipeline API container
	@docker exec -it frostbyte-pipeline-api /bin/bash

shell-db: ## Open PostgreSQL shell
	@docker exec -it frostbyte-postgres psql -U frostbyte -d frostbyte

shell-redis: ## Open Redis CLI
	@docker exec -it frostbyte-redis redis-cli

test: ## Run tests (when infrastructure is running)
	@cd pipeline && python -m pytest

lint: ## Run linting
	@cd pipeline && ruff check .
	@cd packages/admin-dashboard && npm run lint

fmt: ## Format code
	@cd pipeline && ruff format .
	@cd packages/admin-dashboard && npm run format
