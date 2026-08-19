# AuthForge Level 2 — John the Ripper Offline Cracking Laboratory

## Executive Summary
Level 2 of AuthForge transitions from an online login attack surface to an **offline password-hash cracking laboratory**. By supplying students with formatted hash files (`challenge.txt`), students use **John the Ripper** locally on their personal machines. This design offloads computationally heavy guessing attacks from the cloud host (Render/AWS) to student laptops while providing a authentic cybersecurity learning experience.

---

## Pedagogical Objectives
1. **Understand Offline vs. Online Attacks**: Differentiate between sending HTTP login requests over a network versus cracking hashes offline at maximum CPU/GPU speeds.
2. **Master John the Ripper Workflow**:
   - Wordlist attacks (`john --wordlist=dict.txt challenge.txt`)
   - Mutating rules (`john --rules --wordlist=dict.txt challenge.txt`)
   - Hash format auto-detection and hash identification
3. **Experience Defensive Hash Architecture**: Compare the cracking speed of legacy fast hashes (SHA-256) versus modern memory-hard password hashes (Argon2id).

---

## Challenge Tiers & Difficulty Progression

| Tier | Challenge ID | Hash Algorithm | Password Complexity | Learning Objective |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Easy)** | `JR-XXX-EASY` | `SHA-256` | Weak wordlist word (e.g. `shadow88`) | Learn basic John execution and wordlist ingestion. |
| **Tier 2 (Medium)** | `JR-XXX-MEDIUM` | `SHA-256` | Mutated word (e.g. `CyberLab2026!`) | Learn John rules and candidate space expansion. |
| **Tier 3 (Hard)** | `JR-XXX-HARD` | `Argon2id` | Dictionary word with salt | Understand why memory-hard hashes degrade cracking speeds. |

---

## Student Workflow & System Architecture

```text
               AUTHFORGE SERVER
                      │
               Student enters ID (e.g. STU-037)
                      │
                      ▼
             Generate 3 Tier Challenges
                      │
                      ▼
            ┌───────────────────┐
            │  Challenge JR-037 │
            │  Hash File        │
            │  Format:          │
            │  student37:hash   │
            └─────────┬─────────┘
                      │
                      ▼
            Download challenge.txt
                      │
                      ▼
               STUDENT LAPTOP
                      │
                      ▼
             John the Ripper
          (runs locally on laptop)
                      │
             Password Recovered
                      │
                      ▼
             Submit to AuthForge
                      │
                      ▼
             AUTHFORGE SERVER
           Verify Answer Hash
                      │
             ┌────────┴────────┐
             ▼                 ▼
          Correct           Incorrect
             │                 │
             ▼                 ▼
          Solved           Try Again
             │
             ▼
        Leaderboard
```

---

## Hash File Formats for John the Ripper

John the Ripper reads standard user-hash format files (`username:hash`).

### Example 1: SHA-256 Hash Format (`JR-EASY` / `JR-MEDIUM`)
```text
student37:a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e
```

### Example 2: Argon2id Hash Format (`JR-HARD`)
```text
student37:$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$5z9s...
```

---

## API Specifications

### 1. Initialize Student Challenge
- **Endpoint**: `POST /challenge/start`
- **Payload**: `{"student_code": "STU-037"}`
- **Response**:
  ```json
  {
    "student_code": "STU-037",
    "challenges": [
      {
        "challenge_id": "JR-037-EASY",
        "tier": "EASY",
        "hash_type": "SHA-256",
        "status": "ACTIVE"
      },
      {
        "challenge_id": "JR-037-MEDIUM",
        "tier": "MEDIUM",
        "hash_type": "SHA-256",
        "status": "ACTIVE"
      },
      {
        "challenge_id": "JR-037-HARD",
        "tier": "HARD",
        "hash_type": "Argon2id",
        "status": "ACTIVE"
      }
    ]
  }
  ```

### 2. Download Hash File
- **Endpoint**: `GET /challenge/download/{challenge_id}`
- **Response**: File download `challenge_JR-037-EASY.txt` with content: `student37:<hash>`

### 3. Submit Recovered Password
- **Endpoint**: `POST /challenge/submit`
- **Payload**: `{"challenge_id": "JR-037-EASY", "password": "cyberlab2026"}`
- **Response**:
  ```json
  {
    "status": "success",
    "message": "CORRECT! Password verified.",
    "challenge_id": "JR-037-EASY",
    "time_taken_seconds": 92.4
  }
  ```

### 4. Classroom Leaderboard
- **Endpoint**: `GET /leaderboard`
- **Response**: Ranks students by number of tiers completed and total time taken.

---

## Database Schema (SQLite)

```sql
CREATE TABLE IF NOT EXISTS challenge_hashes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_code TEXT NOT NULL,
    challenge_id TEXT UNIQUE NOT NULL,
    tier TEXT NOT NULL, -- EASY, MEDIUM, HARD
    hash_type TEXT NOT NULL, -- SHA256, ARGON2ID
    username TEXT NOT NULL,
    hash_value TEXT NOT NULL,
    plain_password TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE', -- ACTIVE, SOLVED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    time_taken_seconds REAL
);
```

---

## Summary of Educational Benefits
- Zero server performance degradation with 70 simultaneous students.
- Realistic cybersecurity workflow using industry-standard tool **John the Ripper**.
- Clear conceptual demonstration of why modern password hashing (Argon2id) protects user credentials against offline GPU/CPU cracking.
