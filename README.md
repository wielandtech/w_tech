# WielandTech Portfolio & Blog

A modern Django-based personal portfolio and blog platform built with best practices and clean architecture.

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
git clone https://github.com/username/wielandtech.git
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
```
DATABASE_URL=postgresql://...
SECRET_KEY=your-secret-key
REDIS_URL=redis://...
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Start development server:
```bash
python manage.py runserver
```

## 📝 License

[BSD 3-Clause License](LICENSE)

## 📫 Contact

- Website: [wielandtech.com](https://wielandtech.com)
- Email: raphael@wielandtech.com
- GitHub: [@wielandtech](https://github.com/wielandtech)