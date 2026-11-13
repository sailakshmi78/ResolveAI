# ResolveAI — AI-Powered Workplace Companion

ResolveAI is an AI-powered workplace companion designed to help employees, especially freshers, understand company processes, find reliable information, troubleshoot workplace issues, and manage approval requests.

Instead of depending on seniors for every small doubt, employees can use ResolveAI to access company-specific guidance and get structured assistance.

## Key Features

### 1. AI Solution
- Ask questions about company documentation.
- Retrieve relevant information using semantic search.
- Generate context-aware answers grounded in available knowledge sources.

### 2. Find Guidance
- Find company-specific policies and workplace guidance.
- Access relevant information to make informed decisions.

### 3. Track Issue
- Create and track workplace issues.
- Check the status of previously submitted tickets.
- Get guidance for resolving common blockers.

### 4. Approval Center
- Submit workplace approval requests.
- Review pending requests.
- Support reviewer-based approval workflows.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, Django |
| Database | MySQL 8.0 |
| AI Model | Ollama – Qwen 2.5 (1.5B) |
| Embeddings | Sentence Transformers |
| Vector Search | FAISS |
| Frontend | HTML, CSS, JavaScript |

## Project Structure

```text
ResolveAI/
│
├── apps/
│   └── core/
│
├── company_docs/
│   ├── models.py
│   ├── search_service.py
│   └── views.py
│
├── config/
│   ├── settings.py
│   ├── settings_deploy.py
│   ├── urls.py
│   └── wsgi.py
│
├── templates/
│   └── core/
│
├── requirements.txt
├── .gitignore
└── manage.py
```

## Getting Started

### Prerequisites

- Python 3.13+
- MySQL 8.0
- Ollama
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/sailalakshmi78/ResolveAI.git
cd ResolveAI
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a local `.env` file and configure the required Django and MySQL environment variables.

Set your database credentials securely. Never commit `.env` or expose passwords and secret keys.

The deployment settings use environment-based MySQL configuration.

### 5. Configure Ollama

Install Ollama and download the model:

```bash
ollama pull qwen2.5:1.5b
```

Make sure the Ollama service is running before using AI-powered features.

### 6. Run the Application

After configuring your MySQL database and environment variables:

```bash
python manage.py migrate
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Privacy and Security

- Database credentials and secret keys are kept outside the repository.
- Private company documents and knowledge-base files are excluded from public Git tracking.
- Company-specific information should only be added through authorized sources.

## Project Status

**Development and local testing:** Ongoing.

ResolveAI has been uploaded to GitHub. The application is currently maintained as a local development project; public production deployment is not yet available.

## Author

**Sai Lakshmi Karanam**

GitHub: [@sailalakshmi78](https://github.com/sailalakshmi78)

---

*ResolveAI — Helping employees find answers, overcome blockers, and navigate workplace processes with confidence.*
