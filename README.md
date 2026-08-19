# AuthForge Level 1: Vulnerable Login Lab 🛡️⚡

**AuthForge** is an educational cybersecurity laboratory designed to demonstrate how vulnerable authentication systems function, how password-guessing attacks operate in a controlled environment, and how defensive controls can be progressively introduced.

---

## 🎯 Level 1 Purpose & Philosophy

Level 1 establishes the **baseline vulnerable authentication system**. The application deliberately lacks defensive mechanisms (such as rate limiting, account lockout, CAPTCHA, or password hashing) so that students can observe server-side behavior, timing, and log output during authentication attempts.

```
Build vulnerable system → Understand authentication → Observe attack behavior → Measure weaknesses → Add defenses (Level 2+)
```

---

## ⚠️ Intentionally Present Vulnerabilities (Level 1)

1. **V1 — No Rate Limiting**: The server processes unlimited authentication requests per second.
2. **V2 — No Account Lockout**: Repeated login failures do not lock or disable accounts.
3. **V3 — Unhashed Credential Storage**: Passwords in the local database are stored plainly for direct comparison and inspection.
4. **V4 — No CAPTCHA / Bot Defense**: Automated requests face no interactive challenges.
5. **V5 — No Artificial Delay**: Verification executes as quickly as possible.
6. **V6 — Single-Factor Only**: Relies solely on basic Username + Password verification.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- `git`

### 2. Environment Setup

```bash
# Clone repository
git clone https://github.com/shivambhadane/BruteLab.git
cd BruteLab

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Launching AuthForge

Start the FastAPI application server locally:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running, navigate to:
- **Login Page**: `http://127.0.0.1:8000`
- **API Health**: `http://127.0.0.1:8000/health`
- **Dashboard**: `http://127.0.0.1:8000/dashboard` (Requires authentication)

---

## 🔑 Lab Test Accounts

The local database (`data/authforge.db`) automatically initializes with these lab accounts:

| Username | Password | Role |
| :--- | :--- | :--- |
| `testuser` | `password123` | Standard Test User |
| `labuser` | `cyberlab2026` | Laboratory Account |
| `student` | `studentpass` | Student Account |
| `admin` | `admin123` | System Administrator |

---

## 📡 API Endpoints

### `GET /`
Renders the interactive AuthForge login interface.

### `POST /login`
Authenticates credentials. Accepts both HTML form data and JSON payloads.

**JSON Request:**
```json
{
  "username": "testuser",
  "password": "password123"
}
```

**JSON Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "Authentication successful.",
  "username": "testuser"
}
```

**JSON Failure Response (401 Unauthorized):**
```json
{
  "status": "failed",
  "message": "Invalid username or password."
}
```

### `GET /dashboard`
Renders the authenticated control panel and live authentication log viewer.

### `GET /api/logs`
Returns the recent log entries recorded in `logs/auth.log`.

---

## 📜 Attack Observability & Logging

Every login attempt automatically appends a timestamped log entry to `logs/auth.log`:

```text
2026-08-19 07:30:21 | username=testuser | result=FAILED
2026-08-19 07:30:35 | username=testuser | result=SUCCESS
```

To monitor authentication events live from your terminal:
```bash
tail -f logs/auth.log
```
Or view the live updating stream built directly into the AuthForge Dashboard UI.

---

## 🧪 Running Automated Tests

Run the test suite using `pytest`:

```bash
PYTHONPATH=. ./venv/bin/pytest -v
```

---

## 📁 Repository Structure

```
BruteLab/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application routes
│   ├── database.py      # SQLite connection & seed schema
│   ├── models.py        # Pydantic schemas
│   ├── auth.py          # Vulnerable verification & logging logic
│   ├── templates/
│   │   ├── login.html   # Login interface
│   │   └── dashboard.html # Authenticated dashboard & log console
│   └── static/
│       └── style.css    # Modern dark mode design system
├── data/
│   └── authforge.db     # Local SQLite database instance
├── docs/
│   └── v1.md            # PRD - AuthForge Level 1 Specification
├── logs/
│   └── auth.log         # Authentication event log stream
├── tests/
│   └── test_auth.py     # pytest test suite
├── requirements.txt
├── README.md
├── .gitignore
└── LICENSE
```

---

## ⚖️ Educational Disclaimer
This repository is built strictly for **educational cybersecurity research** in isolated local environments. Never run authentication attacks against external systems or unauthorized targets.
