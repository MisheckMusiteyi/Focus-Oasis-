# Advanced Focus - School Portal Workspace

An industry-standard, secure, and production-ready **Student and Admin Portal** backend and frontend designed for the **Focus Oasis Foundation**.

This project resolves the performance, concurrency, and security limitations of the initial Streamlit & Google Sheets prototype by transitioning to a robust **Three-Tier Architecture** utilizing **FastAPI**, **SQLAlchemy ORM** (fully SQL-compliant), and a responsive modern HTML5/JS client with **Tailwind CSS**.

---

## Key Advanced Architectures

1. **Secure Database Layer:**
   - Powered by **SQLAlchemy ORM**.
   - Supports local lightweight **SQLite** for instant zero-setup development.
   - Fully optimized for production-grade cloud databases like **PostgreSQL** with customized Connection Pooling settings (`pool_size`, `max_overflow`, `pool_recycle`).
   - Enforces **Relational Schema Constraints** (e.g. Student IDs dynamically Cascade-Delete linked Fee Payments, Attendance, and Performance logs).

2. **Enterprise Security & Auth:**
   - Fully hashes and encrypts student and administrator passwords using **bcrypt** with `passlib`. No plain text credentials.
   - Implements state-of-the-art **JWT (JSON Web Tokens)** OAuth2 password bearer token validation for all stateful user endpoints.
   - Enforces Role-Based Access Control (RBAC): separating `/api/admin/*` and `/api/student/*` contexts.

3. **High Concurrency performance:**
   - Written in highly concurrent, asynchronous Python FastAPI.
   - Solves Google Sheets API rate-limiting crashes under multiple logins.
   - Clean separation of UI loading state from backend database queries.

---

## Directory Structure

```text
Advanced Focus/
├── backend/
│   ├── database.py       # SQLAlchemy connection engine & sessions setup
│   ├── models.py         # Relational database models (Admin, Student, Fee, Grade, etc.)
│   ├── schemas.py        # Pydantic data modeling and JSON schemas
│   ├── auth.py           # Bcrypt password hashing & JWT handlers
│   └── main.py           # REST API Route entrypoints & CORS configuration
├── frontend/
│   ├── index.html        # Clean, Tailwind-designed secure login workspace
│   ├── dashboard.html    # Unified dynamic Student and Admin dashboards view
│   └── app.js            # Unified Client-Side controller handling JWT sessions
├── requirements.txt      # Modular backend library dependencies
└── README.md             # Developer documentation and deployment manuals
```

---

## Setup & Running Guide

### 1. Backend Installation

1. Navigate to the workspace:
   ```bash
   cd "Advanced Focus"
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the local development server (it will automatically create `advanced_focus.db` in SQLite):
   ```bash
   uvicorn backend.main:app --reload
   ```
   *The Swagger UI will now be available for testing at:* `http://127.0.0.1:8000/docs`

### 2. Frontend Launch

Since the frontend is a pure Single Page App (SPA) architecture, you don't need any build steps!
Simply open the `frontend/index.html` file inside any standard web browser, or launch a simple static file server:
```bash
cd frontend
python -m http.server 8080
```
Then visit `http://localhost:8080` in your web browser.

---

## How to Migrate from Google Sheets to PostgreSQL/SQLite

Transitioning your live data is simple:

1. **Export Google Sheets to CSV:**
   - Navigate to your "Focus Oasis Foundation" Google Sheets workbook.
   - For each sheet tab (e.g. "Student Logins", "Students", "Fee Payments", "Performance", "Attendance View", "Admin Logins"), export/download as `.csv`.

2. **Load CSVs into Python Database Seed script:**
   You can easily write a simple Python script to parse these files and insert them into your new SQL tables using SQLAlchemy:
   ```python
   import pandas as pd
   from backend.database import SessionLocal
   from backend.models import Student, Admin
   from backend.auth import get_password_hash

   db = SessionLocal()

   # Example: Migrate Admin Logins
   df = pd.read_csv("Admin_Logins.csv")
   for idx, row in df.iterrows():
       hashed_pw = get_password_hash(row["Password"])  # Hashes secure password instantly
       admin = Admin(username=row["Username"], password_hash=hashed_pw, email=row.get("Email"))
       db.add(admin)
   db.commit()
   print("Migrated administrators!")
   ```
