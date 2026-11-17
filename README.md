# Turium AI Knowledge Inbox 📬⚡

> A production-style, minimalist semantic knowledge inbox and Retrieval-Augmented Generation (RAG) system. Designed to save short plain-text notes and web articles, segment them using an intentional recursive boundary chunker, store vector representations in an embedded SQLite database, and answer questions with strictly grounded responses and cited sources.

Built for the **Turium AI Interview Assignment**.

---

## 📑 Table of Contents
1. [Architecture & System Flow](#-architecture--system-flow)
2. [Quickstart: Running Locally](#-quickstart-running-locally)
3. [AI Provider Configuration](#-ai-provider-configuration)
4. [Testing Suite](#-testing-suite)
5. [Testing with Postman (1-Click Collection)](#-testing-with-postman-1-click-collection)
6. [API Specification & cURL Examples](#-api-specification--curl-examples)
7. [Non-Functional Expectations & Deep-Dive Rationale](#-non-functional-expectations--deep-dive-rationale)
   - [Chunking Approach Rationale](#1-chunking-approach-rationale)
   - [Vector Store Choice](#2-vector-store-choice)
   - [What Breaks at Scale?](#3-what-breaks-at-scale)
   - [Production Roadmap](#4-production-roadmap)
   - [Debuggability & Code Quality](#5-debuggability--code-quality)
8. [Project File Structure](#-project-file-structure)
9. [Assignment Requirements Checklist](#-assignment-requirements-checklist)

---

## 🏛️ Architecture & System Flow

```
                                  ┌──────────────────────────┐
                                  │   React 18 SPA Frontend  │
                                  │   (Tailwind, Hooks, UI)  │
                                  └─────────────┬────────────┘
                                                │ HTTP / REST
                                                ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI Application                                │
│  ┌─────────────────────────┐  ┌───────────────────────┐  ┌─────────────────────┐  │
│  │      POST /ingest       │  │       GET /items      │  │     POST /query     │  │
│  └────────────┬────────────┘  └───────────┬───────────┘  └──────────┬──────────┘  │
│               │                           │                         │             │
│       ┌───────▼────────┐                  │                 ┌───────▼────────┐    │
│       │ Web Scraper    │                  │                 │ Query Embedder │    │
│       │ (httpx, lxml)  │                  │                 │ (Gemini/OpenAI/│    │
│       └───────┬────────┘                  │                 │  Local Vector) │    │
│               ▼                           │                 └───────┬────────┘    │
│       ┌────────────────┐                  │                         │             │
│       │ Recursive      │                  │                         ▼             │
│       │ Boundary       │                  │                 ┌────────────────┐    │
│       │ Chunker        │                  │                 │ Top-k Cosine   │    │
│       └───────┬────────┘                  │                 │ Similarity     │    │
│               ▼                           │                 │ Search (NumPy) │    │
│       ┌────────────────┐                  │                 └───────┬────────┘    │
│       │ Embedder       │                  │                         │             │
│       │ (Gemini/OpenAI/│                  │                         ▼             │
│       │  Local Vector) │                  │                 ┌────────────────┐    │
│       └───────┬────────┘                  │                 │ Grounded LLM   │    │
│               │                           │                 │ Prompt with    │    │
│               │                           │                 │ Source Citation│    │
│               ▼                           ▼                 └───────┬────────┘    │
│  ┌──────────────────────────────────────────────────────────────────▼──────────┐  │
│  │                        SQLite Database Engine                               │  │
│  │      • items table:  raw content, metadata, counts, timestamps              │  │
│  │      • chunks table: embeddings, char_start/end offsets, cascade foreign key│  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart: Running Locally

### Prerequisites
- **Python 3.10+** (tested on Python 3.13)
- Windows, macOS, or Linux

### 1. Clone the Repository
```bash
git clone <repository_url>
cd tURIUM
```

### 2. Set Up Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and configure your API keys (optional — see [AI Provider Configuration](#-ai-provider-configuration) below).

### 5. Start the Server
```bash
python run.py
```

The application will start immediately. Open your browser:
- **Interactive Web App**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🤖 AI Provider Configuration

The application is built with a flexible multi-provider adapter that supports **Google Gemini**, **OpenAI**, and an **offline Local Fallback**:

```env
# In .env:

# 1. Google Gemini (Active by default if key provided)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_CHAT_MODEL=gemini-3-flash-preview

# 2. OpenAI (Optional alternative)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini

# 3. Provider selection: "auto", "gemini", "openai", or "local"
AI_PROVIDER=auto
```

> **Zero-Friction Offline Fallback**: If no API key is provided, the application **does not crash**. It automatically activates a built-in deterministic subword-hashing vectorizer (384 dimensions) and an extractive synthesizer. This allows any evaluator or CI environment to run and test the complete pipeline out of the box with zero external dependencies.

---

## 🧪 Testing Suite

The repository contains 15 isolated unit and integration tests covering chunking logic, HTML sanitization, vector math, API routes, and validation errors.

Run the test suite using `python -m pytest`:

```bash
python -m pytest -v
```

### Test Output:
```
tests/test_api.py::test_health_check PASSED                              [  6%]
tests/test_api.py::test_ingest_note_success PASSED                       [ 13%]
tests/test_api.py::test_ingest_url_mocked PASSED                         [ 20%]
tests/test_api.py::test_ingest_validation_failure PASSED                 [ 26%]
tests/test_api.py::test_query_knowledge_inbox PASSED                     [ 33%]
tests/test_api.py::test_query_empty_knowledge_base PASSED                [ 40%]
tests/test_api.py::test_delete_item PASSED                               [ 46%]
tests/test_chunker.py::test_chunker_empty_text PASSED                    [ 53%]
tests/test_chunker.py::test_chunker_short_text PASSED                    [ 60%]
tests/test_chunker.py::test_chunker_preserves_paragraphs PASSED          [ 66%]
tests/test_chunker.py::test_chunker_overlap PASSED                       [ 73%]
tests/test_scraper.py::test_scraper_fetch_and_extract_mocked PASSED      [ 80%]
tests/test_scraper.py::test_scraper_http_error_handling PASSED           [ 86%]
tests/test_vector_store.py::test_vector_store_cosine_similarity PASSED   [ 93%]
tests/test_vector_store.py::test_vector_store_empty PASSED               [100%]
============================= 15 passed in 1.25s ==============================
```

---

## 📮 Testing with Postman (1-Click Collection)

A pre-configured Postman Collection is included at [`postman_collection.json`](postman_collection.json).

### How to Import:
1. Open **Postman**.
2. Click **Import** (top left).
3. Select `postman_collection.json` from the repository root.
4. Click **Import**.

### What is Included:
1. `1. Ingest Text Note (POST /ingest)`: Ingests a plain note $\to$ returns `201 Created`.
2. `2. Ingest Web URL (POST /ingest)`: Fetches a URL server-side, cleans HTML, chunks and embeds $\to$ `201 Created`.
3. `3. List Saved Items (GET /items)`: Lists items with metadata and chunk counts $\to$ `200 OK`.
4. `4. Query Knowledge Inbox (POST /query)`: Executes semantic search and grounded LLM QA $\to$ `200 OK`.
5. `5. Error Handling - Invalid URL (POST /ingest)`: Validates bad URLs $\to$ returns `422 Unprocessable Content`.
6. `6. Error Handling - Empty Content (POST /ingest)`: Validates empty payloads $\to$ returns `422 Unprocessable Content`.
7. `7. Error Handling - Non-Existent Item (GET /items/{id})`: Verifies 404 response $\to$ `404 Not Found`.
8. `8. System Health & Models (GET /health)`: Verifies system health and active model metadata $\to$ `200 OK`.

---

## 📡 API Specification & cURL Examples

### 1. Ingest Content (`POST /ingest`)
Accepts either a plain text note or a web URL.

**Request (Text Note):**
```bash
curl -X POST "http://127.0.0.1:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "note",
    "title": "System Architecture",
    "content": "Turium uses recursive boundary chunking, SQLite vector storage, and grounded Gemini LLM synthesis.",
    "metadata": { "tag": "core" }
  }'
```

**Request (Web URL):**
```bash
curl -X POST "http://127.0.0.1:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "url",
    "content": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
    "title": "RAG Overview"
  }'
```

**Response (`201 Created`):**
```json
{
  "id": "47450fea-804a-4d79-9ee3-01680cc22ccf",
  "source_type": "note",
  "title": "System Architecture",
  "url": null,
  "content_preview": "Turium uses recursive boundary chunking...",
  "char_count": 105,
  "word_count": 13,
  "chunk_count": 1,
  "created_at": "2026-11-17T09:30:57.473146+00:00",
  "metadata": { "tag": "core" }
}
```

---

### 2. List Saved Items (`GET /items`)
Returns a paginated list of saved items with metadata.

**Request:**
```bash
curl -X GET "http://127.0.0.1:8000/items?limit=10&offset=0"
```

**Response (`200 OK`):**
```json
{
  "items": [
    {
      "id": "47450fea-804a-4d79-9ee3-01680cc22ccf",
      "source_type": "note",
      "title": "System Architecture",
      "url": null,
      "content_preview": "Turium uses recursive boundary chunking...",
      "char_count": 105,
      "word_count": 13,
      "chunk_count": 1,
      "created_at": "2026-11-17T09:30:57.473146+00:00",
      "metadata": { "tag": "core" }
    }
  ],
  "total": 1
}
```

---

### 3. Query Knowledge Inbox (`POST /query`)
Executes cosine similarity retrieval across all chunks and generates a grounded response with source citations.

**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What chunking strategy does Turium use?",
    "top_k": 3,
    "min_score": 0.05
  }'
```

**Response (`200 OK`):**
```json
{
  "query": "What chunking strategy does Turium use?",
  "answer": "Turium uses recursive boundary chunking with 500-character target window and 100-character overlap [Source 1].",
  "sources": [
    {
      "item_id": "47450fea-804a-4d79-9ee3-01680cc22ccf",
      "chunk_id": "1d18ff7f-2708-441e-9132-ab3826fd034a",
      "source_title": "System Architecture",
      "source_type": "note",
      "url": null,
      "chunk_index": 0,
      "snippet": "Turium uses recursive boundary chunking...",
      "similarity_score": 0.8921
    }
  ],
  "retrieval_count": 1,
  "provider": "gemini",
  "model": "gemini-3-flash-preview",
  "latency_ms": 1150.4
}
```

---

### 4. Delete an Item (`DELETE /items/{id}`)
Removes an item and cascade-deletes its vector chunks from SQLite.

**Request:**
```bash
curl -X DELETE "http://127.0.0.1:8000/items/47450fea-804a-4d79-9ee3-01680cc22ccf"
```

---

## 🧠 Non-Functional Expectations & Deep-Dive Rationale

### 1. Chunking Approach Rationale
- **Strategy**: Recursive Boundary-Aware Chunking ([app/services/chunker.py](app/services/chunker.py)).
- **Why not fixed-character slicing?** Hard character slicing (e.g. slicing every 500 chars) arbitrarily splits words and sentences in half, damaging semantic density and vector fidelity.
- **Why not pure sentence splitting?** Real-world documents have paragraphs ranging from 10 characters to 4,000 characters. Pure sentence splitting yields uneven chunk sizes that harm embedding quality.
- **Our Solution**:
  - Hierarchical separator cascade: Paragraphs (`\n\n`) $\to$ Newlines (`\n`) $\to$ Sentence terminators (`. `, `! `, `? `) $\to$ Words (` `).
  - **Target Chunk Size**: 500 characters (~100–125 tokens), balancing retrieval granularity with sufficient context.
  - **Sliding Overlap**: 100 characters (~20–25 tokens), preventing contextual loss for queries matching near boundaries.
  - **Offset Auditability**: Tracks exact `char_start` and `char_end` relative to parent document for UI highlighting and verification.

---

### 2. Vector Store Choice
- **Selection**: Embedded SQLite database ([app/db/database.py](app/db/database.py)) + in-process NumPy cosine similarity ([app/services/vector_store.py](app/services/vector_store.py)).
- **Why SQLite over External Vector DBs (Pinecone / Weaviate / Milvus)?**
  1. **Zero External Infrastructure**: No Docker containers, no external cloud account setup, no network hop latency for vector lookups.
  2. **Relational Co-location & ACID Guarantees**: Metadata, raw content, and vector representations live in the same transactional boundary. Deleting an item cascade-deletes all associated chunks in a single ACID transaction (`ON DELETE CASCADE`).
  3. **Performance for Target Scale**: Vectorized matrix multiplication in NumPy (`np.dot(matrix, query_vec)`) executes in **under 2 milliseconds** for thousands of chunks.
  4. **Portability**: The entire database is a single portable file (`knowledge_inbox.db`).

---

### 3. What Breaks at Scale?

| Dimension | Scale Threshold | Failure Mode | Production Architecture Mitigation |
|---|---|---|---|
| **Vector Search** | >100,000 chunks | Linear scan $O(N)$ dot products will cause CPU and latency spikes (>50ms). | Migrate to `sqlite-vec` or dedicated vector DB (pgvector / Qdrant) with HNSW graph indexing ($O(\log N)$). |
| **URL Ingestion** | High-volume concurrent scraping | Synchronous event loop scraping causes timeouts or blocks server threads. | Offload scraping to distributed worker queues (Celery / BullMQ / Redis Streams) with proxy rotation. |
| **DB Concurrency** | >50 concurrent writes | SQLite default locking causes write contention (`database is locked`). | Enabled WAL mode (`PRAGMA journal_mode=WAL`), or migrate to PostgreSQL for multi-tenant concurrent writes. |
| **LLM Context Window** | 20+ large documents | Passing excessive chunks causes context stuffing and "lost in the middle" attention degradation. | Implement two-stage retrieval: retrieve top-20 candidates $\to$ cross-encoder re-ranking (e.g. Cohere or bge-reranker) $\to$ pass top-4 to LLM. |

---

### 4. Production Roadmap
If evolving this prototype into an enterprise platform:
1. **Asynchronous Task Architecture**: Ingestion and embedding jobs decoupled via Celery/RabbitMQ, returning an immediate task ID with status polling or WebSocket notifications.
2. **Hybrid Search (Sparse + Dense)**: Combine BM25 full-text keyword indexing (SQLite FTS5) with dense vector embeddings using Reciprocal Rank Fusion (RRF).
3. **Token Streaming**: Implement Server-Sent Events (SSE) on `/query` so LLM tokens stream to the UI in real time rather than waiting for complete generation.
4. **Tenant Isolation & Security**: Add JWT/OAuth2 authentication, user workspace separation, and row-level security.
5. **Embedding & Response Cache**: Redis caching layer for repeated query embeddings and identical prompt responses.

---

### 5. Debuggability & Code Quality
- **Structured Logging (`app/core/logging.py`)**: Every incoming request is stamped with a unique `x-request-id` header and logs execution duration (`duration_ms`), HTTP method, route, and status code.
- **Sensible HTTP Status Codes**:
  - `200 OK`: Successful retrieval or deletion
  - `201 Created`: Item successfully ingested, chunked, and embedded
  - `400 Bad Request`: Validation failure on user input
  - `404 Not Found`: Non-existent item ID requested
  - `422 Unprocessable Content`: Schema/type validation mismatch
  - `502 Bad Gateway`: External web scraping failed or upstream AI API error
  - `500 Internal Server Error`: Unhandled application exception
- **Standardized Error Envelope**:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "The request payload failed validation.",
      "details": [{ "field": "body -> content", "message": "When type is 'url', content must be a valid HTTP or HTTPS URL..." }]
    }
  }
  ```

---

## 📂 Project File Structure

```
tURIUM/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # REST endpoints (/ingest, /items, /query, /health)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic settings & dynamic provider resolution
│   │   ├── logging.py          # Structured JSON & console logging
│   │   └── errors.py           # App exceptions & error response formatter
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py         # SQLite connection, WAL mode & migrations
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic v2 validation models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scraper.py          # Server-side HTML fetching & text cleaning
│   │   ├── chunker.py          # Intentional recursive boundary chunker
│   │   ├── embedder.py         # Multi-provider (Gemini, OpenAI, Local Fallback)
│   │   ├── vector_store.py     # NumPy matrix cosine similarity search
│   │   └── rag_service.py      # Prompt synthesis & grounded citations
│   ├── static/
│   │   └── index.html          # Production React 18 SPA (served directly by FastAPI)
│   ├── __init__.py
│   └── main.py                 # FastAPI application factory & middleware
├── frontend/                   # Standalone React + TypeScript Vite project source
│   ├── src/
│   │   ├── App.tsx
│   │   ├── hooks/
│   │   │   ├── useInbox.ts
│   │   │   └── useQuery.ts
│   │   └── types.ts
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Isolated temporary database fixture
│   ├── test_chunker.py         # Unit tests for chunking boundaries & offsets
│   ├── test_scraper.py         # Unit tests for HTML cleaning & errors
│   ├── test_vector_store.py    # Unit tests for vector dot product
│   └── test_api.py             # Integration tests for all endpoints
├── Turium_AI_Interview_Assignment.pdf
├── postman_collection.json     # Ready-to-import Postman test collection
├── requirements.txt
├── pytest.ini
├── run.py                      # One-click startup script
└── README.md                   # Complete architectural documentation
```

---

## 🏆 Assignment Requirements Checklist

| Requirement | Implementation Detail | Status |
|---|---|:---:|
| **1. Ingest text notes (plain text)** | `POST /ingest` with `type="note"`; auto-titles, counts words/chars | ✅ Complete |
| **2. Ingest URLs (server-side)** | `POST /ingest` with `type="url"`; `httpx` + `lxml` strips boilerplate | ✅ Complete |
| **3. Intentional chunking strategy** | Recursive boundary chunker (`\n\n`, `.?!`), 500 chars window, 100 overlap | ✅ Complete |
| **4. Vector embeddings** | Google Gemini (`gemini-embedding-001`), OpenAI, or Local Fallback | ✅ Complete |
| **5. Vector storage** | Embedded SQLite `chunks` table + vectorized NumPy cosine similarity | ✅ Complete |
| **6. Top-k chunk retrieval** | Filter by similarity threshold, rank descending, return top-k | ✅ Complete |
| **7. Grounded LLM QA with citations** | Strict system prompt enforcing citations (`[Source N]`) | ✅ Complete |
| **8. React Frontend with hooks** | Responsive SPA using `useState`, `useEffect`, `useCallback`, `useMemo` | ✅ Complete |
| **9. Structured logging & debuggability**| Request ID tracking (`x-request-id`), timing middleware, structured logs | ✅ Complete |
| **10. Clear errors & sensible status codes** | Standardized error envelope (`200`, `201`, `400`, `404`, `422`, `502`) | ✅ Complete |
| **11. Tradeoff awareness documentation** | Detailed sections on chunking, vector store, scaling, and production | ✅ Complete |
