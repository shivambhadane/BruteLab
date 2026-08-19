# BruteLab — Cybersecurity Password Security Laboratory

**BruteLab** is an interactive, educational cybersecurity web application built to demonstrate authentication security, online vs. offline password-cracking methodologies, defensive password hashing, and tool usage with **John the Ripper**.

---

## 🚀 Key Laboratory Modules

### Level 1: Vulnerable Online Authentication Laboratory
- Teaches online credential brute-forcing (e.g., using Hydra / Medusa / Python scripts).
- Plaintext / weak baseline credential verification.
- Demonstrates online attack footprints and failure rate monitoring.

### Level 2: John the Ripper Offline Hash Cracking Laboratory
- Teaches offline password-cracking workflows using **John the Ripper**.
- Students download target hash files (`challenge.txt`) and run local GPU/CPU dictionary cracking attacks on their own machines.
- Features **3 Progressive Difficulty Tiers**:
  - **`JR-EASY` (SHA-256)**: Basic dictionary wordlist ingestion (`john --wordlist=dict.txt challenge.txt`).
  - **`JR-MEDIUM` (SHA-256)**: Rule mutations and special character variations (`john --rules --wordlist=dict.txt challenge.txt`).
  - **`JR-HARD` (Argon2id)**: Memory-hard salted hash comparison demonstrating how modern cryptographic hashing degrades cracking speeds.

---

## 🛠️ Architecture & Tech Stack

- **Backend**: Python 3.14 / FastAPI
- **Database**: SQLite (`data/brutelab.db`)
- **Password Hashing**: `SHA-256`, `Argon2id` (`argon2-cffi`)
- **Frontend**: Clean Minimal Developer Interface (GitHub Dark Theme)
- **Test Suite**: pytest / FastAPI TestClient

---

## 📋 Installation & Running Locally

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/shivambhadane/BruteLab.git
cd BruteLab

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
Open `http://localhost:8000` in your web browser.

### 3. Run Test Suite
```bash
PYTHONPATH=. pytest -v
```

---

## 💡 Student Workflow (John the Ripper Lab)

1. **Select Student ID**: Enter or select your assigned student identifier (e.g., `STU-001` through `STU-070`).
2. **Select Challenge Tier**: Choose `JR-EASY`, `JR-MEDIUM`, or `JR-HARD`.
3. **Download Hash File**: Click **Download Hash File** to save `challenge.txt` locally.
4. **Execute John the Ripper**:
   ```bash
   # Tier 1 Easy Wordlist Attack
   john --wordlist=passwords.txt challenge.txt

   # Tier 2 Medium Rule Mutation Attack
   john --rules --wordlist=passwords.txt challenge.txt

   # Show Cracked Passwords
   john --show challenge.txt
   ```
5. **Submit Recovered Password**: Paste your plaintext answer into BruteLab to verify completion.

---

## 🔒 Security Notice & Disclaimer
BruteLab is designed strictly for classroom educational purposes and defensive security training. Unauthorized access or scanning against non-consensual targets is strictly prohibited.
