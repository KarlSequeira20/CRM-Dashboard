# 🏠 AHA Smart Homes — AI-Powered CRM Intelligence Platform

[![Streamlit App](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![Ollama](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com/)
[![Twilio](https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=Twilio&logoColor=white)](https://www.twilio.com/)
[![Zoho](https://img.shields.io/badge/Zoho_CRM-EE2E24?style=for-the-badge&logo=zoho&logoColor=white)](https://www.zoho.com/crm/)

A fully automated, production-grade CRM intelligence system that pulls all data from Zoho CRM across every module, stores it with zero data loss in a Supabase PostgreSQL cloud database, performs deep SQL analytics, and generates AI-driven executive insights using a private local Llama 3.2 model.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    %% Node Definitions
    Zoho([<b>Zoho CRM API</b><br/>Live Data Source])
    Sync{<b>Sync Engine</b><br/>Incremental Extraction}
    Supa[(<b>Supabase Cloud</b><br/>PostgreSQL + JSONB)]
    Metrics[<b>Analytics Engine</b><br/>SQL Funnel Logic]
    Ollama[[<b>Ollama AI Node</b><br/>Local Llama 3.2 Agent]]
    Dash[<b>Executive UI</b><br/>Streamlit Dashboard]
    WhatsApp[<b>WhatsApp Pulse</b><br/>Twilio Delivery]

    %% Connections
    Zoho ---|Pull| Sync
    Sync ---|Upsert| Supa
    Supa ---|Query| Metrics
    Metrics ---|Payload| Ollama
    Ollama ---|Visual| Dash
    Ollama ---|Direct| WhatsApp

    %% Styling
    classDef source fill:#EE2E24,stroke:#333,stroke-width:2px,color:#fff;
    classDef storage fill:#3ECF8E,stroke:#333,stroke-width:2px,color:#fff;
    classDef logic fill:#6366F1,stroke:#333,stroke-width:2px,color:#fff;
    classDef delivery fill:#FF4B4B,stroke:#333,stroke-width:2px,color:#fff;

    class Zoho source;
    class Supa storage;
    class Sync,Metrics,Ollama logic;
    class Dash,WhatsApp delivery;
```

---

## 📂 Project Structure

```text
AHA Smart Homes Project /
├── backend/
│   ├── src/
│   │   ├── ai/
│   │   │   └── ollamaClient.js      # Executive Briefing Generator (Llama 3.2 Agent)
│   │   ├── analytics/
│   │   │   └── metrics.js           # Funnel & Revenue Logic (PostgreSQL + JS)
│   │   ├── api/
│   │   │   ├── aiRoutes.js          # REST API for insights & triggers
│   │   │   └── server.js            # Express API Server (Webhook & Sync Trigger)
│   │   ├── auth/
│   │   │   └── zohoAuth.js          # Zoho OAuth 2.0 Client & Token Rotation
│   │   ├── config/
│   │   │   └── env.js               # Centralized Environment config & validation
│   │   ├── ingestion/
│   │   │   ├── leads.js             # Zoho Leads Dynamic Module Extraction
│   │   │   └── deals.js             # Zoho Deals Ingestion logic
│   │   ├── scheduler/
│   │   │   └── index.js             # Main Orchestrator: Sync → SQL → AI → WhatsApp
│   │   ├── utils/
│   │   │   ├── schema.sql           # Database schema definitions (JSONB ELT)
│   │   │   └── supabaseClient.js    # Supabase (PostgreSQL) Client adapter
│   │   └── whatsapp/
│   │       └── twilioClient.js      # Twilio WhatsApp Dispatcher
│   ├── package.json                 # Backend dependencies & pipeline scripts
│   └── .env                         # Sensitive configuration (NOT committed)
└── dashboard.py                     # Premium Streamlit Dashboard (15+ Charts)
```

---

## ⚙️ Setup & Installation

### Prerequisites
- **Python 3.10+**
- **[Ollama](https://ollama.com/)** with `llama3.2:1b` pulled locally
- A **Zoho CRM** account with API credentials
- A **Supabase** project
- A **Twilio** account with WhatsApp Sandbox enabled

### 1. Install Dependencies
```bash
# Install Python dependencies
pip install streamlit pandas plotly supabase requests python-dotenv

# Install Node.js backend dependencies
cd backend
npm install
```

### 2. Configure Environment Variables
Create a `.env` file in the `backend/` directory with your Zoho, Supabase, and Twilio credentials.

### 3. Apply Database Schema
Open your Supabase project → SQL Editor → paste the contents of `backend/src/utils/schema.sql` → click **Run**.

---

## 🚀 Running the System

| Mode | Command | Description |
| :--- | :--- | :--- |
| **Backend API** | `npm run start:api` | Handles WhatsApp webhooks & triggers |
| **Dashboard** | `streamlit run dashboard.py` | Launches the live UI |
| **Manual Sync** | `npm run start:pipeline` | Triggers a fresh data & AI run |

---

## 🛠️ Tech Stack & Design Justification

### Core Infrastructure
- **Node.js (Backend)**: Chosen for its asynchronous non-blocking I/O, ideal for orchestrating multiple API calls (Zoho, Supabase, Twilio) and handling concurrent WhatsApp webhooks.
- **Python/Streamlit (Frontend)**: Selected for rapid iteration of data-heavy dashboards. Streamlit's ecosystem allows for professional Plotly integration with minimal boilerplate.
- **Supabase (PostgreSQL + JSONB)**: 
    - **PostgreSQL**: Robust relational support for structured metrics (CRM Deals, Contacts).
    - **JSONB**: Utilized for the **ELT (Extract, Load, Transform) pattern**. Storing raw CRM data in JSONB ensures zero data loss during sync, even if Zoho adds custom fields later.
- **Ollama / Llama 3.2**: 
    - **Choice**: Open-source local LLM over OpenAI.
    - **Justification**: 100% data privacy (no sensitive lead info leaves the machine) and $0 inference cost.
- **Twilio WhatsApp API**: Industry standard for reliable, high-deliverability mobile alerts.

---

## 🏗️ Design Decisions & Trade-offs

1. **SQL Math vs. LLM Math**: 
    - *Decision*: All funnel calculations (Lead-to-Won rates, Total Revenue) are performed in the PostgreSQL layer using complex SQL aggregations. 
    - *Rationale*: LLMs are prone to "hallucinations" when performing arithmetic. Offloading math to SQL ensures 100% accurate KPIs, allowing the AI to focus on **qualitative strategy**.
2. **Synchronous Dashboard Refresh**: 
    - *Decision*: The Streamlit "Refresh" button triggers a synchronous backend pipeline.
    - *Trade-off*: While slower than an async trigger, it provides the executive with immediate feedback and a guaranteed "Success" state once the UI updates.
3. **Immutability in Sync**: 
    - *Decision*: We use a `sync_logs` table to track every fetch.
    - *Rationale*: Provides a reliable audit trail for debugging Zoho API issues and ensures idempotency during incremental syncs.

---

## 🧠 Product Thinking: The "CRO Persona"

This system isn't just a data bridge; it's a **context engine**. 
- **Strategic Persona**: The AI is prompted as a Chief Revenue Officer. Instead of saying "Leads are up by 10%," it says, "We have a 10% surge in Facebook leads, but conversion velocity is slowing—recommend re-allocating budget to High-Value Deals."
- **Daily Pulse**: The WhatsApp summary is limited to 400 characters, forcing the AI to provide only the "Critical Gap" and "Immediate Action," respecting the executive's time.



> [!IMPORTANT]
> **Privacy First**: All AI analysis is performed 100% locally on your machine. No CRM data ever leaves your infrastructure for processing.
