.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.PHONY: up
up: ## Start API + Redis (expects an external ITERLAB_DATABASE_URL)
	$(COMPOSE) up --build

.PHONY: up-bundled
up-bundled: ## Start API + Redis + a bundled PostgreSQL
	$(COMPOSE) --profile bundled-db up --build

.PHONY: down
down: ## Stop and remove containers
	$(COMPOSE) --profile bundled-db down

.PHONY: logs
logs: ## Tail API logs
	$(COMPOSE) logs -f api

.PHONY: install
install: ## Install the backend package with dev extras
	cd backend && pip install -e '.[dev]'

.PHONY: test
test: ## Run the backend test suite
	cd backend && pytest

.PHONY: lint
lint: ## Lint + type-check the backend
	cd backend && ruff check . && mypy iterlab

.PHONY: fmt
fmt: ## Auto-format the backend
	cd backend && ruff check --fix . && ruff format .
