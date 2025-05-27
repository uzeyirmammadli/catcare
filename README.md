# CatCare - Cat Management System

A comprehensive web application for managing cat care and health records, built with Flask and modern Python technologies.

## Features

- User authentication and authorization
- Cat profile management
- Health record tracking
- Cloud storage integration
- RESTful API endpoints
- Responsive web interface

## Technical Stack

Backend: Python, Flask, Flask-SQLAlchemy, Flask-JWT-Extended | Database: PostgreSQL, SQLAlchemy ORM | Cloud Services: Google Cloud Platform, Cloud SQL, Cloud Storage | Authentication: JWT, Flask-Login | Development Tools: Git, Alembic, Virtual Environments

## Prerequisites

- Python 3.8+
- PostgreSQL
- Google Cloud Platform account (for deployment)
- Git

## Installation

1. Clone the repository:
```bash
git clone https://github.com/uzeyirmammadli/catcare
cd catcare
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
- Create a `.env` file in the root directory
- Add necessary environment variables (see `env_variables.yaml` for reference)

5. Initialize the database:
```bash
flask db upgrade
```

## Configuration

1. Database Configuration:
- Update database connection settings in `config.py`
- Ensure PostgreSQL is running and accessible

2. Cloud Storage:
- Configure Google Cloud credentials
- Update storage bucket settings in `cloud_storage.py`

## Running the Application

Development mode:
```bash
flask run
```

Production mode:
```bash
gunicorn app:app
```

## Project Structure

```
catcare/
├── catcare/
│   ├── templates/      # HTML templates
│   ├── static/         # Static files (CSS, JS, images)
│   ├── __init__.py     # Application factory
│   ├── models.py       # Database models
│   ├── routes.py       # Route handlers
│   ├── forms.py        # Form definitions
│   └── api.py          # API endpoints
├── migrations/         # Database migrations
├── requirements.txt    # Project dependencies
├── config.py          # Configuration settings
└── app.py             # Application entry point
```

## API Documentation

The API documentation is available at `/api/docs` when running the application.

## Deployment

1. Configure Google Cloud Platform:
- Set up Cloud SQL instance
- Configure Cloud Storage bucket
- Update `app.yaml` with deployment settings

2. Deploy to Google Cloud:
```bash
gcloud app deploy
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

