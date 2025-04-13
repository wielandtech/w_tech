#!/bin/bash
echo "Redeploying the WielandTech Django App, plus stack..."

docker compose version

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
until [ "$(docker inspect -f '{{.State.Health.Status}}' $(docker compose ps -q web))" == "healthy" ]; do
  echo "Waiting for web container to become healthy..."
  sleep 2
done

echo "Running Django management commands..."
docker compose -f docker-compose.yml exec web python manage.py makemigrations --noinput
docker compose -f docker-compose.yml exec web python manage.py migrate --noinput
docker compose -f docker-compose.yml exec web python manage.py collectstatic --noinput

echo "Deployment complete."
