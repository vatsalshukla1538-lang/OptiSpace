# Automated Classroom Scheduling System - MITS Gwalior
**B.Tech Information Technology (First Semester Micro Project)**

---

## 1. Project Overview & Requirements
This application is a compact, beginner-friendly micro project designed for **Madhav Institute of Technology & Science (MITS), Gwalior**.

It solves the manual timetable scheduling problem by modeling it as a **Constraint Satisfaction Problem (CSP)** using a **Backtracking Algorithm** in Python.

### Core Features (As per Project Specification):
1. **Data Upload**:
   - Admins can easily enter or upload lists of teachers, subjects, and rooms (manual forms + bulk CSV upload with downloadable templates).
2. **Smart Scheduling**:
   - The system automatically creates a complete weekly timetable with **zero overlapping conflicts** using CSP Backtracking.
3. **Manual Edits**:
   - Admins can drag and drop classes across the weekly grid to make manual adjustments.
   - If a manual change causes a room clash, teacher clash, or batch clash, the system warns the user immediately and prevents the collision.
4. **Easy Export**:
   - The final schedule can be downloaded as an **Excel (.xlsx)** or **PDF** file with a single click.

### Project Goals:
- **Save Time**: Generates a conflict-free semester timetable in seconds rather than weeks of manual trial-and-error.
- **Better Room Usage**: Ensures every classroom and laboratory is allocated efficiently without double-booking.

---

## 2. Technology Stack
- **Frontend**: React 19, Vite, clean vanilla CSS design system (`index.css`), HTML5 Drag-and-Drop.
- **Backend**: Python 3.12, Django 6, Django REST Framework (DRF), `djangorestframework-simplejwt` (JWT Auth).
- **Algorithm Engine**: Pure Python CSP Backtracking with Forward Checking and Most Constrained Variable (MRV) ordering.
- **Database**:
  - **SQLite3** (`db.sqlite3`): Zero-configuration database for instant local evaluation.
  - **PostgreSQL**: Used by the Docker deployment setup.
- **Export Engines**: `openpyxl` (Excel .xlsx), `reportlab` (PDF), Python standard `csv`.

---

## 3. Quick Start (Windows PowerShell)

### Normal Startup
Starts both Django backend and Vite frontend without deleting records:
```powershell
.\start-all.ps1
```
- **Web App**: [http://localhost:5173/](http://localhost:5173/)
- **Backend API**: [http://127.0.0.1:8000/api/](http://127.0.0.1:8000/api/)

### Default Demo Credentials
These credentials are for local demonstrations only. Do not use them on a public deployment.

| Role | Username | Password | Capabilities |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Full access: Enter/upload rooms, faculty, subjects; generate timetable; drag-and-drop edit; export |
| **Viewer** | `viewer` | `viewer123` | Read-only access: View weekly timetable, filter by semester/batch, search, export Excel/PDF |

### Reset / Seed Authentic MITS Data
To seed authentic MITS IT Department data (Semesters I, III, V, VII: 87 courses, 200 sessions, 11 rooms, 19 faculty):
```powershell
cd backend
python seed.py
```

---

## 4. Manual Step-by-Step Setup

### Step 4.1: Backend (Terminal 1)
```powershell
cd backend

# 1. Install dependencies
python -m pip install -r requirements.txt

# 2. Run migrations
python manage.py migrate

# 3. Seed users & authentic MITS dataset
python seed.py

# 4. Start Django server
python manage.py runserver 127.0.0.1:8000
```

### Step 4.2: Frontend (Terminal 2)
```powershell
cd frontend

# 1. Install packages
npm.cmd install

# 2. Start Vite server
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

---

## 5. PostgreSQL Database Configuration

For local development with PostgreSQL, the application connects when `DATABASE_URL` is provided in `backend/.env`.

1. Create a database in PostgreSQL:
   ```sql
   CREATE DATABASE classroom_db;
   CREATE USER classroom_user WITH PASSWORD 'classroom_pass';
   GRANT ALL PRIVILEGES ON DATABASE classroom_db TO classroom_user;
   ```
2. Create `backend/.env` (see `backend/.env.example`):
   ```env
   SECRET_KEY=mits-classroom-secret-key
   DEBUG=True
   DATABASE_URL=postgresql://classroom_user:classroom_pass@127.0.0.1:5432/classroom_db
   ```
3. Run migrations and seed data:
   ```powershell
   cd backend
   python manage.py migrate
   python seed.py
   ```
*If `DATABASE_URL` is omitted, the project defaults to SQLite (`db.sqlite3`) for instant zero-configuration demonstration.*

---

## 6. Upload to GitHub

1. Install Git, then open PowerShell in this project folder.
2. Check that the local database, `.env` files, and installed packages are ignored:
   ```powershell
   git status --short --ignored
   ```
   The root `.gitignore` excludes these local-only files. Keep real secrets in `.env` files or GitHub/hosting-provider secrets, never in committed files.
3. Create an empty repository on GitHub (do not initialize it with a README), then run:
   ```powershell
   git init
   git add .
   git status --short
   git commit -m "Prepare classroom scheduling project"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
   git push -u origin main
   ```

## 7. Run the deployment setup

The included Docker Compose setup runs the React frontend, Django API, and PostgreSQL database together. Install Docker Desktop, copy the root environment template, and replace the example values:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose up --build
```

Open [http://localhost:8080/](http://localhost:8080/). The database persists in a Docker volume between restarts. Stop the services with `Ctrl+C` or `docker compose down`; `docker compose down -v` also deletes the database volume.

Before deploying publicly:
- Set a new, long random `SECRET_KEY` and a strong PostgreSQL password in the hosting provider's environment settings.
- Use a URL-safe PostgreSQL password (letters and numbers) with the provided Compose `DATABASE_URL` configuration.
- Set `ALLOWED_HOSTS` to the actual backend/domain hostnames. Configure HTTPS at the hosting provider or reverse proxy.
- Do not run `python seed.py` on a public deployment: it creates the published demo accounts `admin` / `admin123` and `viewer` / `viewer123`. For initial production access, create an administrator with `docker compose exec backend python manage.py createsuperuser`.
- Treat this Docker setup as a self-hosted/container deployment. A platform with separate static-site and backend services will need the frontend's `VITE_API_URL` set to the deployed API base URL and matching Django CORS settings.

## 8. Streamlined Project File Structure

The project has been cleaned and consolidated so it is easy to navigate and defend:

```text
micro project/
├── README.md                  # Single project documentation & viva guide
├── start-all.ps1              # One-click startup script for backend & frontend
├── init-demo.ps1              # Demo database seed script
├── docker-compose.yml         # Local/container deployment services
├── .env.example               # Safe template for Compose configuration
├── backend/
│   ├── Dockerfile             # Django production container
│   ├── manage.py              # Django CLI entrypoint
│   ├── requirements.txt       # Python dependencies (the only text file in backend)
│   ├── .env.example           # Example PostgreSQL configuration
│   ├── seed.py                # Single script to seed default users & authentic MITS dataset
│   ├── config/                # Django project settings & URLs
│   │   ├── settings.py
│   │   └── urls.py
│   └── scheduling/            # Core timetable application
│       ├── models.py          # Relational models (Room, Teacher, Course, Schedule, etc.)
│       ├── views.py           # REST API endpoints, Excel & PDF export handlers, RBAC
│       ├── solver.py          # CSP Backtracking Algorithm (Forward Checking & MRV heuristic)
│       ├── serializers.py     # DRF serializers with collision validation
│       ├── it_data.py         # Authentic MITS IT curriculum & faculty definitions
│       ├── tests.py           # 55 automated unit, integration, and system tests
│       └── urls.py            # API routing
└── frontend/
    ├── Dockerfile             # React build and Nginx web server
    ├── nginx.conf             # SPA routing and API proxy
    ├── package.json           # Frontend dependencies (React 19, Vite, Axios)
    ├── vite.config.js         # Vite build configuration
    └── src/
        ├── main.jsx           # React application mount point
        ├── App.jsx            # Main app: Login screen, Header, Navigation tabs, Overview
        ├── Timetable.jsx      # Core timetable: Weekly grid, drag & drop, exports, conflict alerts
        ├── Manage.jsx         # Data upload: Enter / CSV upload for Rooms, Teachers, Subjects
        ├── api.js             # Axios client with JWT authentication & token refresh
        └── index.css          # Unified CSS stylesheet
```

---

## 9. First-Semester Viva Defense Guide (Q&A)

### Q1: What is a Constraint Satisfaction Problem (CSP)?
**Answer**: A CSP models scheduling using three parts:
1. **Variables**: What needs to be placed (each 1-hour weekly session of a subject).
2. **Domains**: The valid slots where it can go (combinations of `Room`, `Day`, and `TimeSlot`).
3. **Constraints**: Hard rules that must never be broken (no room clashes, no teacher double-booking, no student batch double-booking, room capacity $\ge$ student count, lab vs. lecture room matching).

### Q2: How does the Backtracking algorithm work?
**Answer**:
- **Forward step**: The algorithm takes the first session, finds a valid slot and room that meets all constraints, assigns it, and recursively calls itself to schedule the next session.
- **Dead end**: If it reaches a session where no room/slot is available without a clash, it stops exploring that branch.
- **Backtrack**: The function returns `False`, unwinds the call stack by one step, undoes the last assignment, and tries an alternate slot.
- **Base case**: When all required class sessions are placed with 0 conflicts, the algorithm returns `True`.

### Q3: What is Forward Checking?
**Answer**: Standard backtracking only checks if the current assignment conflicts with past assignments. **Forward Checking** looks ahead at all remaining unscheduled subjects. If assigning a class wipes out all available options for any future subject (domain wipeout), the algorithm backtracks immediately. This prevents exploring dead-end branches.

### Q4: How does manual drag-and-drop prevent conflicts?
**Answer**: In `Timetable.jsx`, when an Admin drags a class to a new day/time slot, the frontend sends a validation request to `/api/schedule/validate/`. The backend checks all hard constraints (is the room free? is the teacher free? is the batch free?). If any clash is detected, the move is rejected, a red warning alert is displayed, and the class snaps back to its original slot.

### Q5: How do PDF and Excel exports work?
**Answer**:
- **Excel (.xlsx)**: Generated using Python's `openpyxl` library with styled table headers, course codes, faculty names, and rooms.
- **PDF**: Generated using `reportlab` with landscape table formatting and clean borders.
- Both formats can be downloaded by both Admins and Viewers with a single click.

### Q6: How does JWT authentication work in your project?
**Answer**:
- On login, Django verifies the password and issues a short-lived `access_token` and a longer `refresh_token`.
- React stores the token and attaches `Authorization: Bearer <token>` to requests.
- An Axios interceptor in `api.js` catches 401 errors when the token expires and automatically fetches a fresh access token using the refresh token.

### Q7: What are the current academic limitations?
**Answer**:
1. **Academic prototype**: This is a first-semester B.Tech micro project, not a production cloud deployment.
2. **Greedy room allocation**: It chooses the smallest suitable room to reduce wasted seats, which is a greedy heuristic rather than exhaustive global optimization.
3. **Discrete 1-hour slots**: Classes are scheduled in 1-hour blocks (09:00 - 16:00).
