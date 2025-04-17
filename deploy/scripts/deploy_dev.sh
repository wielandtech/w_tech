#!/bin/bash
#deploy/scripts/deploy.sh
start_time=$(date +%s)

echo "[$( date '+%H:%M:%S' )] Redeploying the WielandTech Django App, plus stack..."

set -e  # Exit on error

cd /opt/w_tech_dev

echo "[$( date '+%H:%M:%S' )] Pulling latest code..."
git pull origin development

echo "[$( date '+%H:%M:%S' )] Stopping old containers..."
docker compose -p w_tech_dev -f docker-compose.yml down --remove-orphans

echo "[$( date '+%H:%M:%S' )] Building new images..."
docker compose -p w_tech_dev -f docker-compose.yml build

echo "[$( date '+%H:%M:%S' )] Starting containers..."
docker compose -p w_tech_dev -f docker-compose.yml up -d

# Wait for build to complete
wait $BUILD_PID

# Optimized health check with timeout
echo "[$( date '+%H:%M:%S' )] Waiting for web container to become healthy..."
timeout 60 bash -c 'until [ "$(docker inspect -f "{{.State.Health.Status}}" $(docker compose ps -q web))" == "healthy" ]; do sleep 2; done'

echo "[$( date '+%H:%M:%S' )] Running Django management commands..."
docker compose -p w_tech_dev docker-compose.yml exec web python manage.py makemigrations --noinput
docker compose -p w_tech_dev exec web python manage.py migrate --noinput
docker compose -p w_tech_dev exec web python manage.py collectstatic --noinput

end_time=$(date +%s)
duration=$((end_time - start_time))
echo "[$( date '+%H:%M:%S' )] Deployment complete. Total duration: ${duration} seconds"