# 🎓 JiEdu – School Management System

![Django](https://img.shields.io/badge/Django-4.x-green.svg)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-In%20Development-orange)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

---

> 🏫 **JiEdu** is a comprehensive Django-based school management system designed to streamline academic and administrative processes — from student enrollment to AI-driven attendance tracking.

---

## 📚 Core Features

### 🧑‍🎓 Student Enrollment
- Register and manage student profiles
- Class assignments and progression tracking

### 👨‍🏫 Staff Management
- Add, edit, and manage staff records
- Role and subject allocations

### 🗓️ Timetable Management
- **Manual Scheduling** – Create class timetables easily
- **Face Recognition** – AI-assisted smart scheduling and attendance

### 📊 Staff Workload Management
- Track teaching hours and workload balance
- Auto-generate workload reports

### 📌 Attendance Management
- Daily attendance with filtering by date, class, or subject
- Integration with facial recognition for auto-marking

### 💸 Fee Management
- **MPesa Integration** – Seamless mobile payment tracking
- **Bank Transfers** – Manage and reconcile offline payments
- Auto-reminders, payment receipts, and report exports

---

## 🛠️ Built With

| Tech        | Description                    |
|-------------|--------------------------------|
| Django      | Backend web framework          |
| PostgreSQL  | Relational database            |
| OpenCV      | Face recognition for attendance|
| Bootstrap   | Responsive UI design           |
| MPesa API   | Mobile payment integration     |

---

## 📷 Screenshots

> _Coming soon..._ (Consider adding screenshots or GIFs of major features)

---

## 🚀 Getting Started

### 🔧 Prerequisites

Make sure you have the following installed:

- Python 3.10+
- Django 4.x
- PostgreSQL
- Git
- pip / venv

---

### 📦 Installation

```bash
# Clone the repository
git clone https://github.com/your-username/jiedu.git
cd jiedu

# Create virtual environment
python -m venv env
source env/bin/activate   # On Windows use: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env      # Then edit .env with DB credentials, API keys, etc.

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
