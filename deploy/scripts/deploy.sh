#!/bin/bash
echo "Redeploying the WielandTech Django App, plus stack..."

set -e  # Exit on error

cd /opt/w_tech

echo "Pulling latest code..."
git pull origin development

echo "Stopping old containers..."
docker compose -f docker-compose.yml down

# Build and start containers in parallel
echo "Building and starting containers..."
docker compose -f docker-compose.yml build --parallel &
BUILD_PID=$!

# Start containers while build is still running
docker compose -f docker-compose.yml up -d

# Wait for build to complete
wait $BUILD_PID

# Improved: Wait for Django to be fully ready
echo "Waiting for Django app to be ready..."
timeout 60 bash -c 'until docker compose exec web python manage.py check --deploy --fail-level ERROR; do sleep 2; done'

# Run Django management commands
echo "Running Django management commands..."
docker compose -f docker-compose.yml exec web python manage.py makemigrations --noinput
docker compose -f docker-compose.yml exec web python manage.py migrate --noinput
docker compose -f docker-compose.yml exec web python manage.py collectstatic --noinput

echo "Deployment complete."
