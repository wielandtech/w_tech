# === Directories ===
PROD_DIR=/opt/w_tech
DEV_DIR=/opt/w_tech_dev

# === Compose project names ===
PROD_PROJECT=w_tech
DEV_PROJECT=w_tech_dev

# === Default targets ===
.PHONY: help
help:
	@echo "Usage:"
	@echo "  make deploy-prod          Deploy production environment"
	@echo "  make deploy-dev           Deploy development environment"
	@echo "  make down-prod            Stop and remove production containers"
	@echo "  make down-dev             Stop and remove development containers"
	@echo "  make migrate-prod         Run migrations in production"
	@echo "  make migrate-dev          Run migrations in development"
	@echo "  make makemigrations-prod  Create migrations in production"
	@echo "  make makemigrations-dev   Create migrations in development"

# === Production Targets ===
deploy-prod:
	cd $(PROD_DIR) && \
	git pull origin main && \
	docker compose -p $(PROD_PROJECT) -f docker-compose.yml down --remove-orphans && \
	docker compose -p $(PROD_PROJECT) -f docker-compose.yml build && \
	docker compose -p $(PROD_PROJECT) -f docker-compose.yml up -d

down-prod:
	cd $(PROD_DIR) && \
	docker compose -p $(PROD_PROJECT) -f docker-compose.yml down --remove-orphans

migrate-prod:
	cd $(PROD_DIR) && \
	docker compose -p $(PROD_PROJECT) exec web python manage.py migrate --noinput

makemigrations-prod:
	cd $(PROD_DIR) && \
	docker compose -p $(PROD_PROJECT) exec web python manage.py makemigrations

# === Development Targets ===
deploy-dev:
	cd $(DEV_DIR) && \
	git pull origin development && \
	docker compose -p $(DEV_PROJECT) -f docker-compose.yml down --remove-orphans && \
	docker compose -p $(DEV_PROJECT) -f docker-compose.yml build && \
	docker compose -p $(DEV_PROJECT) -f docker-compose.yml up -d

down-dev:
	cd $(DEV_DIR) && \
	docker compose -p $(DEV_PROJECT) -f docker-compose.yml down --remove-orphans

migrate-dev:
	cd $(DEV_DIR) && \
	docker compose -p $(DEV_PROJECT) exec web python manage.py migrate --noinput

makemigrations-dev:
	cd $(DEV_DIR) && \
	docker compose -p $(DEV_PROJECT) exec web python manage.py makemigrations
