<div align="center">

![AgentNet Logo](https://raw.githubusercontent.com/YOUR_USERNAME/AIML_Project/main/docs/logo.png)

# AgentNet
### *Vision-Driven Multi-Agent Parking Intelligence*

**An autonomous ecosystem of specialized AI agents that transforms raw camera feeds into real-time parking orchestration — from license plate to allocated bay in under 15 seconds.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Supabase](https://img.shields.io/badge/Supabase-Cloud-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Detection-FF6B35?style=for-the-badge&logo=ultralytics&logoColor=white)](https://ultralytics.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

---

## 📸 Dashboard Preview

> **[!TIP]**
> Place a GIF or screenshot of the Neon HUD dashboard here. Use the browser's built-in screen recorder or a tool like [LICEcap](https://www.cockos.com/licecap/) to capture a live session.

```
[Screenshot: Operations View with multi-frame burst capture and agent pipeline matrix]
[Screenshot: Occupancy View with interactive 48-bay topography grid]
[Screenshot: Analytics View with Chart.js vehicle flow histograms]
```

---

## ✨ Key Features

- 🧠 **Multi-Agent Orchestration** — Decentralized pipeline of 5 specialized AI agents (Vision, Optimization, Allocation, SRE, Billing) that communicate via structured handovers.
- 🎯 **Aggregate Trust Score Engine** — Not just OCR. Every detection is filtered using a composite score (`YOLO Confidence × Aspect Ratio Weight × OCR Structural Score`) to eliminate false positives like banners and signs.
- 📸 **Multi-Frame Consensus Voting** — Up to 10 camera frames are analyzed in parallel; the highest-scoring candidate is elected as the final license plate.
- 🅿️ **Best-Fit Bin Packing** — Optimization Agent dynamically assigns the smallest suitable slot to each vehicle (Small/Medium/Large), preserving premium spots for larger vehicles.
- ⚡ **Atomic Transaction Integrity** — Slot updates, active sessions, and audit logs are committed atomically to Supabase, ensuring zero data inconsistency.
- 🛡️ **SRE Guardian** — Built-in Site Reliability Engineering agent monitors inter-agent latency in real-time and raises alerts when degradation exceeds thresholds.
- 🖥️ **Neon HUD Command Suite** — A premium single-page application (SPA) dashboard with real-time slot topography, vehicle flow analytics, and a deployable agent wizard.
- 🔍 **Full Audit Trail** — Every entry and exit event is persisted to a `transactions` table with full metadata (confidence scores, timestamps, agent latency).

---

## 🏗️ How It Works

### The 5-Stage Pipeline

```
[Camera / User Upload]
        │
        ▼
┌───────────────────┐
│  1. VISION AGENT  │  ← YOLOv8 detects plate region
│   Multi-Frame     │  ← EasyOCR reads text from burst
│   Consensus Vote  │  ← Aggregate Trust Score filters noise
└────────┬──────────┘
         │  license_plate + dimensions
         ▼
┌────────────────────────┐
│ 2. OPTIMIZATION AGENT  │  ← Queries Supabase for FREE slots
│   Best-Fit Strategy    │  ← Selects smallest viable bay
└────────┬───────────────┘
         │  optimal_slot_id
         ▼
┌───────────────────────┐
│ 3. ALLOCATION AGENT   │  ← Marks slot as OCCUPIED
│   Atomic Execution    │  ← Creates active_session record
│                       │  ← Logs to transactions (ENTRY)
└────────┬──────────────┘
         │
         ▼
┌───────────────────────┐
│ 4. SRE GUARDIAN       │  ← Records latency of each agent
│   Health Observation  │  ← Raises alerts if > 1000ms
└────────┬──────────────┘
         │
         ▼
┌───────────────────────┐
│ 5. NEON HUD UPDATE    │  ← Dashboard reflects allocation
│   Real-time Sync      │  ← Log terminal logs each event
└───────────────────────┘
```

### Trust Score Calculation
| Component | Weight | Description |
| :--- | :---: | :--- |
| YOLO Confidence | 40% | Raw detection confidence from YOLOv8 |
| Aspect Ratio Score | 30% | License plate width/height ratio validator |
| OCR Structural Score | 30% | Indian plate format regex validator (`AA 00 AA 0000`) |

> [!IMPORTANT]
> Only candidates scoring above **0.6** on the Aggregate Trust Score are considered valid license plates. This eliminates headings, banners, and partial detections.

---

## 🗃️ Database Schema

The system uses 3 PostgreSQL tables hosted on **Supabase**:

| Table | Purpose | Key Columns |
| :--- | :--- | :--- |
| `parking_slots` | Live slot inventory | `slot_number`, `status`, `size_type`, `zone`, `current_vehicle` |
| `active_sessions` | Real-time vehicle tracking | `license_plate`, `slot_id`, `entry_time`, `is_active` |
| `transactions` | Historical audit log | `license_plate`, `action_type` (ENTRY/EXIT), `metadata` (JSONB) |

---

## 🌐 API Reference

| Method | Endpoint | Description |
| :---: | :--- | :--- |
| `POST` | `/api/entry` | Submit multi-frame burst for vehicle entry |
| `POST` | `/api/exit` | Process vehicle exit and calculate billing |
| `POST` | `/api/verify` | Validate QR code against active session |
| `GET` | `/api/slots/all` | Full inventory of all parking bays |
| `GET` | `/api/stats` | Aggregated analytics data for charts |
| `GET` | `/api/infrastructure` | Hardware node health status |
| `GET` | `/api/health` | SRE system report with agent latencies |
| `GET` | `/api/logs` | Latest 20 entry/exit audit records |

---

## ⚙️ Configuration

Create a `.env` file in the project root with the following variables:

| Variable | Required | Description |
| :--- | :---: | :--- |
| `SUPABASE_URL` | ✅ | Your Supabase project URL |
| `SUPABASE_KEY` | ✅ | Your Supabase `anon` or `service_role` API key |

> [!CAUTION]
> Never commit your `.env` file. It is already listed in `.gitignore`. Never hardcode credentials directly in source files.

---

## 🚀 Installation & Setup

### Prerequisites
- Python `3.10+`
- A [Supabase](https://supabase.com) project with the schema applied (see `schema.sql`)
- A YOLOv8 model trained for license plate detection (`best.pt`)

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/AIML_Project.git
cd AIML_Project
```

### 2. Create & Activate Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Create a .env file in the root directory
echo SUPABASE_URL=your_project_url >> .env
echo SUPABASE_KEY=your_anon_key >> .env
```

### 5. Initialize the Database
Open your Supabase project's **SQL Editor** and run the contents of `schema.sql`. This creates the three core tables and seeds the initial parking slots.

```bash
# Optional: Use the seed script for local testing
python seed_db.py
```

### 6. Launch AgentNet
```bash
uvicorn app.main:app --reload
```

Navigate to **[http://127.0.0.1:8000](http://127.0.0.1:8000)** to open the **Neon HUD Command Suite**.

> [!TIP]
> The FastAPI interactive docs at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** allow you to test all API endpoints directly in the browser.

---

## 🧬 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **API Framework** | FastAPI (ASGI) |
| **WSGI Server** | Uvicorn |
| **Object Detection** | YOLOv8 (Ultralytics) |
| **OCR Engine** | EasyOCR |
| **Image Processing** | OpenCV (Headless) |
| **Database** | Supabase (PostgreSQL + PostgREST) |
| **Frontend** | Tailwind CSS, Chart.js, Vanilla JS |
| **Environment** | Python-dotenv |

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built as part of the **AI & Machine Learning (Sem 4)** academic project.

*AgentNet — Where every parking decision is an act of intelligence.*

</div>
