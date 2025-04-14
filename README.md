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
wielandtech/
├── account/          # User auth & profiles
├── actions/          # Activity tracking
├── blog/            # Blog functionality  
├── common/          # Shared utilities
├── core/            # Website core
├── deploy/          # Deployment configs
├── images/          # Image handling
├── nginx/           # Nginx config
├── static/          # Static files
└── wielandtech/     # Project settings
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

## 📝 License

[BSD 3-Clause License](LICENSE)

## 📫 Contact

- Website: [wielandtech.com](https://wielandtech.com)
- Email: raphael@wielandtech.com
- GitHub: [@wielandtech](https://github.com/wielandtech)