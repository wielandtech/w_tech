#!/bin/bash
echo "Redeploying the WielandTech Django App, plus stack..."

set -e  # Exit on error

cd /opt/w_tech

echo "Pulling latest code..."
git pull origin development

echo "Building maintenance page image..."
docker build -t w_tech_maintenance -f deploy/Dockerfile.maintenance .

echo "Setting up port forwarding..."
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 8443

echo "Starting maintenance page..."
docker run -d --name maintenance_page \
    -p 8080:80 \
    -p 8443:443 \
    -v /etc/letsencrypt:/etc/letsencrypt:ro \
    w_tech_maintenance

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

echo "Stopping maintenance page..."
docker stop maintenance_page
docker rm maintenance_page

echo "Removing port forwarding..."
sudo iptables -t nat -D PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo iptables -t nat -D PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 8443

echo "Deployment complete."
