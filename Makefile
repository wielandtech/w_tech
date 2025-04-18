# === Directories ===
PROD_DIR=/opt/w_tech
DEV_DIR=/opt/w_tech_dev

# === Compose project names ===
PROD_PROJECT=w_tech
DEV_PROJECT=w_tech_dev

# === Default targets ===
.PHONY: help test-prod test-dev lint clean logs-prod logs-dev shell-prod shell-dev backup-prod backup-dev install-dev
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
    @echo "  make collectstatic-prod   Collect static files in production"
    @echo "  make collectstatic-dev    Collect static files in development"
    @echo "  make test-prod            Run tests in production"
    @echo "  make test-dev             Run tests in development"
    @echo "  make lint                 Run linting and code quality checks"
    @echo "  make clean                Clean up temporary and cache files"
    @echo "  make logs-prod            View logs for production environment"
    @echo "  make logs-dev             View logs for development environment"
    @echo "  make shell-prod           Open Django shell in production"
    @echo "  make shell-dev            Open Django shell in development"
    @echo "  make backup-prod          Backup production database"
    @echo "  make backup-dev           Backup development database"
    @echo "  make install-dev          Install development dependencies"

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

collectstatic-prod:
    cd $(PROD_DIR) && \
    docker compose -p $(PROD_PROJECT) exec web python manage.py collectstatic --noinput

test-prod:
    cd $(PROD_DIR) && \
    docker compose -p $(PROD_PROJECT) exec web python manage.py test --noinput

logs-prod:
    cd $(PROD_DIR) && \
    docker compose -p $(PROD_PROJECT) logs -f

shell-prod:
    cd $(PROD_DIR) && \
    docker compose -p $(PROD_PROJECT) exec web python manage.py shell

backup-prod:
    cd $(PROD_DIR) && \
    docker compose -p $(PROD_PROJECT) exec db pg_dump -U $(DATABASE_USER) $(DATABASE_NAME) > backup_prod_$$(date +%Y%m%d_%H%M%S).sql

# === Development Targets ===
deploy-dev:
    cd $(DEV_DIR) && \
    git pull origin development && \
    docker compose -p $(DEV_PROJECT) -f docker-compose-dev.yml down --remove-orphans && \
    docker compose -p $(DEV_PROJECT) -f docker-compose-dev.yml build && \
    docker compose -p $(DEV_PROJECT) -f docker-compose-dev.yml up -d

down-dev:
    cd $(DEV_DIR) && \
    docker compose -p $(DEV_PROJECT) -f docker-compose-dev.yml down --remove-orphans

migrate-dev:
    cd $(DEV_DIR) && \
    docker compose -p $(DEV_PROJECT) exec web python manage.py migrate --noinput

makemigrations-dev:
    cd $(DEV_DIR) && \
    docker compose -p $(DEV_PROJECT) exec web python manage.py makemigrations

collectstatic-dev:
    cd $(DEV_DIR) && \
    docker compose -p $(DEV_PROJECT) exec web python manage.py collectstatic --noinput

test-dev:
    cd $(DEV_DIR) && \
    docker compose -p $(DEV_PROJECT) exec web python manage.py test --noinput

logs-dev:
    cd $(DEV_DIR) && \
    docker compose -p $(DEV_PROJECT) logs -f

shell-dev:
    cd $(DEV_DIR) && \
    docker compose -p $(DEV_PROJECT) exec web python manage.py shell

backup-dev:
    cd $(DEV_DIR) && \
    docker compose -p $(DEV_PROJECT) exec db pg_dump -U $(DATABASE_USER) $(DATABASE_NAME) > backup_dev_$$(date +%Y%m%d_%H%M%S).sql

install-dev:
    pip install -r requirements-dev.txt

# === Code Quality ===
lint:
    flake8 .
    black --check .
    isort --check-only .

# === Cleanup ===
clean:
    find . -type d -name "__pycache__" -exec rm -r {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name "*.pyd" -delete
    find . -type f -name ".coverage" -delete
    find . -type d -name "*.egg-info" -exec rm -r {} +
    find . -type d -name "*.egg" -exec rm -r {} +
