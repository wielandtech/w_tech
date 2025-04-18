# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /wielandtech

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy Django project
COPY . .

# Make entrypoint script executable
RUN chmod +x deploy/scripts/docker-entrypoint.sh

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["deploy/scripts/docker-entrypoint.sh"]

# Start Gunicorn server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "wielandtech.wsgi:application"]
