#!/bin/bash

cd /opt/w_tech
git pull origin development
docker-compose -f deploy/docker-compose.yml build
docker-compose -f deploy/docker-compose.yml up -d

docker-compose -f deploy/docker-compose.yml exec web python manage.py migrate --noinput
docker-compose -f deploy/docker-compose.yml exec web python manage.py collectstatic --noinput
