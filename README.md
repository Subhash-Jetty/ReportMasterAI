---
title: ReportMaster AI
emoji: 📊
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Financial Reporting Intelligence Hub powered by RAG
---

# ReportMaster AI — Financial Reporting Intelligence Hub

<div align="center">

**A semantic retrieval system that indexes financial reporting manuals and generates grounded answers using RAG (Retrieval-Augmented Generation)**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 🎯 Problem Statement

An accounting department maintains internal manuals describing financial reporting standards and procedures. Team members preparing reports frequently need clarification on specific accounting rules. **ReportMaster AI** is a semantic retrieval system that indexes reporting manuals and generates grounded answers based on retrieved content.

## 🏗️ Architecture

```
User Query → FastAPI Backend → Sentence-Transformers (Embeddings) → FAISS (Vector Search)
    → Top-K Retrieval → Google Gemini LLM → Grounded Answer with Citations
```

### Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | FastAPI + Uvicorn | REST API server |
| **Embeddings** | sentence-transformers (`all-MiniLM-L6-v2`) | Text → 384-dim vectors |
| **Vector Store** | FAISS (CPU) | Fast similarity search |
| **LLM** | Google Gemini 1.5 Flash | Answer generation |
| **Frontend** | HTML/CSS/JS | Interactive query interface |
| **Deployment** | Docker + Docker Compose | Containerized deployment |

## 📋 Features

- ✅ **Semantic Search**: Find relevant sections across multiple financial manuals
- ✅ **AI-Powered Answers**: Grounded answers with source citations using Google Gemini
- ✅ **Document Management**: Upload, index, and manage financial reporting manuals
- ✅ **Auto-Indexing**: Automatically indexes sample manuals on first startup
- ✅ **Fallback Mode**: Works without API key (returns retrieved context only)
- ✅ **RESTful API**: Full API with Swagger/OpenAPI documentation at `/docs`
- ✅ **Premium UI**: Dark-themed, responsive web interface
- ✅ **Docker Ready**: One-command deployment with Docker Compose

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- (Optional) Google Gemini API key for AI-generated answers

### 1. Clone & Install

```bash
cd ReportMasterAI

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
copy .env.example .env     # Windows
# cp .env.example .env     # Linux/Mac

# Edit .env and add your Google Gemini API key (optional)
# Get a free key at: https://aistudio.google.com/apikey
```

### 3. Run the Server

```bash
python run.py
```

The server starts at **http://localhost:8000**

### 4. Access the Application

- **Web UI**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/query` | Submit a question and get AI-generated answer |
| `GET` | `/api/documents` | Get index status and document list |
| `POST` | `/api/documents/upload` | Upload and index a new document |
| `DELETE` | `/api/documents/{name}` | Remove a document from the index |
| `POST` | `/api/documents/reindex` | Re-index all documents |
| `GET` | `/api/health` | Health check endpoint |

### Example Query

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the five steps for revenue recognition under ASC 606?"}'
```

## 📁 Sample Manuals Included

The system comes pre-loaded with 5 comprehensive financial reporting manuals:

1. **Revenue Recognition (ASC 606)** — Five-step model, contract modifications, disclosures
2. **Financial Statement Preparation** — Balance sheet, income statement, cash flows
3. **Lease Accounting (ASC 842)** — Lessee/lessor accounting, classification, measurement
4. **Internal Controls & SOX Compliance** — COSO framework, Section 302/404, deficiency classification
5. **Tax Reporting (ASC 740)** — Deferred taxes, valuation allowance, uncertain tax positions

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | _(empty)_ | Gemini API key for answer generation |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model |
| `CHUNK_SIZE` | `500` | Text chunk size in characters |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `TOP_K_RESULTS` | `5` | Number of retrieved chunks |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |

## 📂 Project Structure

```
ReportMasterAI/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py             # Configuration settings
│   ├── rag/
│   │   ├── embeddings.py     # Sentence-transformer embeddings
│   │   ├── indexer.py        # Document chunking & FAISS indexing
│   │   ├── retriever.py      # Semantic search retrieval
│   │   └── generator.py      # Gemini answer generation
│   ├── models/
│   │   └── schemas.py        # Pydantic request/response models
│   └── routers/
│       ├── query.py          # Query endpoint
│       └── documents.py      # Document management endpoints
├── data/manuals/             # Financial reporting manuals
├── static/                   # Web frontend
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── run.py                    # Entry point
└── README.md
```

## 📜 License

MIT License — free for educational and commercial use.
