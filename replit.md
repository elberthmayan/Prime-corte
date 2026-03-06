# Prime Corte - Barbershop Booking App

## Overview
A Flask-based barbershop management and scheduling application (in Portuguese). Allows clients to register, log in, book appointments, and message admins. Admins can manage appointments and services.

## Tech Stack
- **Backend:** Python 3.12, Flask 3.0.3, Werkzeug 3.0.1
- **Database:** SQLite (stored at `database/barbearia.db`)
- **Frontend:** Jinja2 templates, plain CSS/JS
- **Production Server:** Gunicorn

## Project Structure
- `app.py` - Main Flask application with all routes
- `database.py` - DB initialization and connection helpers
- `config.py` - (Empty, reserved for config)
- `models.py` - (Empty, reserved for models)
- `templates/` - Jinja2 HTML templates
  - `admin/` - Admin dashboard templates
  - `cliente/` - Client-facing templates
- `static/` - CSS and JS assets
- `database/` - SQLite database file

## Running the App
- Development: `python app.py` (runs on port 5000)
- Production: `gunicorn --bind=0.0.0.0:5000 --reuse-port app:app`

## Default Admin Credentials
- Email: `admin@primecorte.com`
- Password: `admin123`

## Features
- User registration and login (clients and admins)
- Appointment scheduling with professionals (André, Carlos, Mateus)
- Services management (Corte, Corte + Barba, Barba, Sobrancelha)
- Real-time availability check
- In-app messaging between clients and admins
- User profile management
