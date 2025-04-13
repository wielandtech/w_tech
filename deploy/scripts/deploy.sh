#!/bin/bash
echo "Redeploying the WielandTech Django App, plus stack..."

set -e  # Exit on error

cd /opt/w_tech

echo "Pulling latest code..."
git pull origin development

echo "Stopping old containers..."
docker compose -f docker-compose.yml down

echo "Building new images..."
docker compose -f docker-compose.yml build

echo "Starting containers..."
docker compose -f docker-compose.yml up -d

# Wait for the web container to be ready (optional, replace 'healthcheck' with your container's name if applicable)
echo "Waiting for web container to be ready..."
docker compose -f docker-compose.yml exec web bash -c 'until nc -z localhost 8000; do sleep 1; done'

echo "Running Django management commands..."
docker compose -f docker-compose.yml exec web python manage.py makemigrations --noinput
docker compose -f docker-compose.yml exec web python manage.py migrate --noinput
docker compose -f docker-compose.yml exec web python manage.py collectstatic --noinput

echo "Deployment complete."
