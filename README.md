# WielandTech Portfolio & Blog

A modern Django-based personal portfolio and blog platform.

## 🌟 Features

- Dynamic portfolio showcase
- Blog with rich text editing and tags
- User authentication & profiles
- Activity feed and social features  
- Responsive design
- SEO optimized

## 🛠️ Tech Stack

- **Backend**: Django 5.1
- **Database**: PostgreSQL 
- **Cache**: Redis
- **Frontend**: HTML5, CSS3, JavaScript
- **Server**: Nginx, Gunicorn
- **Container**: Docker
- **CI/CD**: GitHub Actions

## 📁 Project Structure

```
w_tech/
├── account/                    # User auth & profiles
│   ├── static/
│   │   └── css/
│   │       └── account.css    # Account styling
│   ├── templates/
│   ├── admin.py
│   ├── authentication.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── actions/                    # Activity tracking
│   ├── admin.py
│   ├── models.py
│   ├── tests.py
│   ├── utils.py
│   └── views.py
├── blog/                      # Blog functionality
│   ├── static/
│   │   └── css/
│   │       ├── blog.css      # Blog styling
│   │       └── blog-dark.css # Dark mode styling
│   ├── templates/
│   │   └── blog/
│   │       ├── base.html
│   │       └── post/
│   └── views.py
├── core/                      # Website core
│   ├── static/
│   │   ├── css/
│   │   │   ├── dark-mode.css # Dark theme
│   │   │   ├── main.css     # Main styling
│   │   │   └── normalize.css # CSS reset
│   │   └── js/
│   │       ├── main.js      # Core JavaScript
│   │       └── theme.js     # Theme switcher
│   └── templates/
│       └── core/
│           ├── about.html
│           ├── base.html
│           ├── index.html
│           └── projects.html
├── deploy/                    # Deployment configs
├── images/                    # Image handling
│   ├── static/
│   │   └── css/
│   │       └── images.css    # Image gallery styling
│   └── templates/
│       └── images/
│           └── base.html
├── nginx/                     # Nginx config
│   └── conf.d/
├── static/                    # Static files
├── wielandtech/              # Project settings
├── .env                      # Environment variables
├── docker-compose.yml        # Docker setup
├── Dockerfile                # Docker image
├── manage.py                 # Django CLI
├── requirements.txt          # Python dependencies
└── README.md                 # Documentation
```

## 🚀 Getting Started

1. Clone repository:
```bash
git clone https://github.com/wielandtech/w_tech.git
cd wielandtech
```

2. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables in `.env`:
```env
# Django settings
DJANGO_SECRET_KEY='your-secret-key'
DEBUG=True
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-ip-address

# Database configuration
DATABASE_NAME=your_db_name
DATABASE_USER=your_db_user
DATABASE_PASSWORD="your-password"
DATABASE_HOST=db
DATABASE_PORT=5432

# Email settings
EMAIL_HOST=mail.your-domain.com
EMAIL_HOST_USER=no-reply@your-domain.com
EMAIL_PASSWORD="your-email-password"
EMAIL_PORT=465
EMAIL_USE_SSL=True

# GitHub webhook
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# Social auth credentials
SOCIAL_AUTH_FACEBOOK_KEY="your-facebook-key"
SOCIAL_AUTH_FACEBOOK_SECRET="your-facebook-secret"

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY="your-google-oauth2-key"
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET="your-google-oauth2-secret"

# Redis configuration
REDIS_IP="your-redis-ip"
REDIS_KEY="your-redis-key"
REDIS_PORT=6379
REDIS_DB=0
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Start development server:
```bash
python manage.py runserver
```

## 🔧 Development

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Docker & Docker Compose

### Testing
```bash
# Run tests
python manage.py test

# Run with coverage
coverage run manage.py test
coverage report
```

### Docker Development
```bash
# Build and start services
docker compose up --build

# Run migrations in container
docker compose exec web python manage.py migrate
```

### Managing Migrations in Docker
```bash
# Drop into a shell in the web container
docker compose exec web bash

# Reset migrations for a specific app
python manage.py migrate app_name zero

# Remove migration files
rm app_name/migrations/0*.py

# Create fresh migration
python manage.py makemigrations app_name

# Apply new migration
python manage.py migrate app_name
```

### Troubleshooting Migrations

If you encounter `relation already exists` errors during migrations:

```bash
# Stop the containers first
docker compose down

# Remove the PostgreSQL volume to start fresh
docker volume rm w_tech_postgres_data

# Rebuild and start the containers
docker compose up --build -d

# Run migrations again
docker compose exec web python manage.py migrate
```

### Restoring Database Backups

To restore a database backup from the host machine:

```bash
# Restore from gzipped SQL backup
zcat db_backups/your_db_name_20250418_020000.sql.gz | \
  docker exec -i w_tech_dev-db-1 psql -U your_db_user -d your_db_name
```

### Creating a Superuser

To create a superuser account in Docker:

```bash
# Access the container shell
docker compose exec web python manage.py createsuperuser

# Follow the prompts:
# - Enter username
# - Enter email
# - Enter password (it won't be visible)
# - Confirm password
```

Alternatively, create a superuser non-interactively:

```bash
# Create superuser with predefined credentials
docker compose exec web python manage.py createsuperuser --noinput --username admin --email admin@example.com
```

Note: When using --noinput, set the DJANGO_SUPERUSER_PASSWORD environment variable first:
```bash
export DJANGO_SUPERUSER_PASSWORD="your-secure-password"
```

## 📝 License

[BSD 3-Clause License](LICENSE)

## 📫 Contact

- Website: [wielandtech.com](https://wielandtech.com)
- Email: raphael@wielandtech.com
- GitHub: [@wielandtech](https://github.com/wielandtech)