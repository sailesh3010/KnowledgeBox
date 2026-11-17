# Turium AI Knowledge Inbox 📬⚡

A minimalist, production-style semantic knowledge inbox and Retrieval-Augmented Generation (RAG) system. Designed to save plain-text notes and web articles, segment them using intentional recursive boundary chunking, store vector embeddings in SQLite, and answer user queries with strictly grounded, cited responses.

Built for the **Turium AI Interview Assignment**.

---

## 🎯 Architecture & Design Highlights

```
                          ┌──────────────────────────┐
                          │   React 18 SPA Frontend  │
                          │   (Tailwind, Hooks, UI)  │
                          └─────────────┬────────────┘
                                        │ HTTP / REST
                                        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Application                             │
│  ┌─────────────────────────┐  ┌────────────────────────────────────────┐  │
│  │     POST /ingest        │  │              POST /query               │  │
│  └────────────┬────────────┘  └───────────────────┬────────────────────┘  │
│               │                                   │                       │
│       ┌───────▼────────┐                  ┌───────▼────────┐              │
│       │ Web Scraper    │                  │ Query Embedder │              │
│       │ (httpx, lxml)  │                  │ (OpenAI/Gemini/│              │
│       └───────┬────────┘                  │  Local Vector) │              │
│               ▼                           └───────┬────────┘              │
│       ┌────────────────┐                          │                       │
│       │ Recursive      │                          ▼                       │
│       │ Boundary       │                  ┌────────────────┐              │
│       │ Chunker        │                  │ Top-k Cosine   │              │
│       └───────┬────────┘                  │ Similarity     │              │
│               ▼                           │ Search (NumPy) │              │
│       ┌────────────────┐                  └───────┬────────┘              │
│       │ Embedder       │                          │                       │
│       │ (OpenAI/Gemini/│                          ▼                       │
│       │  Local Vector) │                  ┌────────────────┐              │
│       └───────┬────────┘                  │ Grounded LLM   │              │
│               │                           │ Prompt with    │              │
│               │                           │ Source Citation│              │
│               ▼                           └───────┬────────┘              │
│  ┌────────────────────────────────────────────────▼────────────────────┐  │
│  │                    SQLite Database Engine                           │  │
│  │      - items table (raw content, metadata, timestamps)              │  │
│  │      - chunks table (embeddings, token offsets, cascade delete)     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Single Command)

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ (optional, only if modifying standalone frontend)

### 1. Clone & Install Dependencies
```bash
git clone <repository_url>
cd tURIUM
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
> **Zero-Friction Fallback**: If you do not have an OpenAI or Gemini API key, the system **works out of the box** using its built-in deterministic local vectorizer and extractive QA synthesizer! To enable full cloud generation:
> - Set `OPENAI_API_KEY=sk-...` (uses `text-embedding-3-small` and `gpt-4o-mini`)
> - OR set `GEMINI_API_KEY=AIza...` (uses `text-embedding-004` and `gemini-2.5-flash`)

### 3. Launch App
```bash
python run.py
```
Open your browser to:
- **Web App**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🧪 Running Tests

The test suite includes 15 isolated unit and integration tests covering chunking, HTML scraping, vector mathematics, REST endpoints, and error validation:

```bash
pytest -v
```

---

## 📐 Non-Functional Expectations & Deep-Dive Rationale

### 1. Chunking Approach Rationale
- **Strategy**: Recursive Boundary-Aware Chunking.
- **Why not fixed-character slicing?** Hard character slicing (e.g. slicing every 500 characters) cuts words and sentences in half, severing semantic relations and diluting vector fidelity.
- **Why not purely sentence-based or paragraph-based?** Real-world documents vary drastically; a single paragraph might be 3,000 characters or 20 characters.
- **Our Implementation (`app/services/chunker.py`)**:
  - Hierarchical separator cascade: Paragraphs (`\n\n`) $\to$ Single newlines (`\n`) $\to$ Sentences (`. `, `! `, `? `) $\to$ Words (` `).
  - **Target Chunk Size**: ~500 characters (~100–125 tokens). Balances semantic density with retrieval precision.
  - **Sliding Overlap**: ~100 characters (~20–25 tokens). Guarantees that query matches straddling boundaries retain adequate context.
  - **Metadata Tracking**: Every chunk stores exact `char_start` and `char_end` offsets relative to the parent document for auditability and highlighting.

---

### 2. Vector Store Choice
- **Selection**: Embedded SQLite database (`knowledge_inbox.db`) with vectorized NumPy cosine similarity.
- **Why SQLite over Pinecone / Weaviate / Milvus?**
  1. **Zero External Infrastructure**: No cloud account required, no local Docker containers, no network hop latency for vector lookups.
  2. **Relational Co-location & ACID Guarantees**: Metadata, raw content, and vector representations live in the same transactional boundary. Deleting an item cleanly cascades and removes all associated vectors in one ACID transaction (`ON DELETE CASCADE`).
  3. **Performance for Target Scale**: Vectorized matrix multiplication in NumPy (`np.dot(matrix, query_vec)`) executes in **sub-millisecond latency** (<2ms) for thousands of chunks.
  4. **Portability**: The entire database is a single file that can be inspected, backed up, or shared.

---

### 3. What Breaks at Scale?

| Dimension | Scale Threshold | Failure Mode | Mitigation / Production Fix |
|---|---|---|---|
| **Vector Search** | >100,000 chunks | Linear scan $O(N)$ dot products will cause CPU and latency spikes (>50ms). | Migrate to `sqlite-vec` extension or dedicated vector database (pgvector / Qdrant) with HNSW graph indexing ($O(\log N)$). |
| **URL Ingestion** | High-volume concurrent scraping | Synchronous event-loop scraping can lead to socket exhaustion, IP blocks, or slow page timeouts blocking threads. | Offload scraping to background task queues (Celery / BullMQ / Redis Streams) with distributed proxy rotation. |
| **Database Concurrency** | >50 concurrent writes | SQLite default locks can trigger `database is locked` errors under heavy concurrent write load. | Enabled WAL mode (`PRAGMA journal_mode=WAL`), or migrate to PostgreSQL for multi-tenant concurrent writes. |
| **LLM Context Window** | 20+ large documents | Passing excessive chunks causes context stuffing, attention degradation ("lost in the middle"), and increased token costs. | Implement a two-stage retrieval pipeline: retrieve top-20 candidates $\to$ apply cross-encoder re-ranking (e.g. Cohere or bge-reranker) $\to$ pass top-4 to LLM. |

---

### 4. Production Roadmap & Architectural Evolutions
If scaling this prototype into a multi-tenant enterprise system:
1. **Asynchronous Worker Architecture**: Decouple ingestion via an event bus (RabbitMQ / Kafka / Redis) so large URL scrapes and batch vector embeddings happen in background worker pools.
2. **Hybrid Search (Sparse + Dense)**: Combine BM25 full-text keyword indexing (using SQLite FTS5) with dense neural embeddings and reciprocal rank fusion (RRF) to capture exact keyword matches (IDs, product names) alongside semantic concepts.
3. **Response Streaming**: Implement Server-Sent Events (SSE) on `/query` so LLM tokens stream to the UI in real time rather than waiting for the entire response to generate.
4. **Tenant Isolation & Access Control**: Add user authentication (JWT / OAuth2), role-based permissions, and row-level security so queries only match chunks belonging to the authorized user.
5. **Caching Layer**: Cache frequent query embeddings and responses in Redis to save LLM tokens and achieve <10ms response times for repeat queries.

---

### 5. Debuggability & Code Quality
- **Structured Logging (`app/core/logging.py`)**: Every incoming request is stamped with a unique `x-request-id` header and logs execution duration (`duration_ms`), HTTP method, route, and status code.
- **Sensible HTTP Status Codes**:
  - `200 OK`: Successful retrieval or deletion
  - `201 Created`: Item successfully ingested, chunked, and embedded
  - `400 Bad Request`: Validation failure on user input
  - `404 Not Found`: Non-existent item ID requested
  - `422 Unprocessable Entity`: Schema/type validation mismatch
  - `502 Bad Gateway`: External web scraping failed or upstream AI API error
  - `500 Internal Server Error`: Unhandled application exception
- **Standardized Error Envelope**:
  ```json
  {
    "error": {
      "code": "SCRAPER_FAILED",
      "message": "Received HTTP 404 while fetching 'https://example.com/missing'",
      "details": { "status_code": 404, "url": "https://example.com/missing" }
    }
  }
  ```

---

## 📡 API Reference & cURL Examples

### 1. Ingest Plain Text Note
```bash
curl -X POST "http://127.0.0.1:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "note",
    "title": "RAG System Notes",
    "content": "Retrieval-Augmented Generation enhances LLM responses by fetching relevant context from a knowledge base."
  }'
```

### 2. Ingest Web URL
```bash
curl -X POST "http://127.0.0.1:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "url",
    "content": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"
  }'
```

### 3. List Saved Items
```bash
curl -X GET "http://127.0.0.1:8000/items"
```

### 4. Query Knowledge Inbox
```bash
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does RAG enhance LLM responses?",
    "top_k": 4
  }'
```

### 5. Delete an Item
```bash
curl -X DELETE "http://127.0.0.1:8000/items/<item_id>"
```

### 6. Health Check
```bash
curl -X GET "http://127.0.0.1:8000/health"
```

---

## 📂 Project Structure

```
tURIUM/
├── app/
│   ├── api/
│   │   └── routes.py           # REST endpoints (/ingest, /items, /query, /health)
│   ├── core/
│   │   ├── config.py           # Pydantic settings & provider resolution
│   │   ├── logging.py          # Structured JSON & console logging
│   │   └── errors.py           # App exceptions & error response formatter
│   ├── db/
│   │   └── database.py         # SQLite connection, schema, transactions
│   ├── models/
│   │   └── schemas.py          # Pydantic v2 validation models
│   ├── services/
│   │   ├── scraper.py          # Server-side HTML fetching & text cleaning
│   │   ├── chunker.py          # Intentional recursive boundary chunker
│   │   ├── embedder.py         # Multi-provider (OpenAI, Gemini, Local)
│   │   ├── vector_store.py     # Vector cosine similarity index
│   │   └── rag_service.py      # Prompt synthesis & grounded citations
│   ├── static/
│   │   └── index.html          # Production React 18 SPA (served by FastAPI)
│   └── main.py                 # FastAPI application factory & middleware
├── frontend/                   # Standalone React + TypeScript Vite project
│   ├── src/
│   │   ├── App.tsx
│   │   ├── hooks/
│   │   └── types.ts
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   ├── conftest.py             # Test isolation fixture with temp SQLite DB
│   ├── test_chunker.py         # Unit tests for chunking boundaries
│   ├── test_scraper.py         # Unit tests for HTML cleaning & errors
│   ├── test_vector_store.py    # Unit tests for vector dot product
│   └── test_api.py             # Integration tests for all endpoints
├── Turium_AI_Interview_Assignment.pdf
├── requirements.txt
├── pytest.ini
├── run.py                      # One-click startup script
└── README.md                   # Full documentation & tradeoff analysis
```

---

## 🏆 Summary Checklist Against Assignment Requirements

| Requirement | Implementation | Status |
|---|---|:---:|
| **1. Ingest text notes** | `POST /ingest` with `type="note"` | ✅ Complete |
| **2. Ingest URLs server-side** | `POST /ingest` with `type="url"` via `httpx` + `lxml` | ✅ Complete |
| **3. Intentional chunking strategy** | Recursive paragraph/sentence/word chunker with overlap | ✅ Complete |
| **4. Vector embeddings** | OpenAI `text-embedding-3-small`, Gemini `text-embedding-004`, or Local Fallback | ✅ Complete |
| **5. Vector storage** | SQLite table + fast NumPy cosine similarity | ✅ Complete |
| **6. Retrieve top relevant chunks** | Vector search by similarity score with top-k ranking | ✅ Complete |
| **7. LLM QA with source citations** | Grounded prompt enforcing `[Source N]` citation | ✅ Complete |
| **8. React Frontend with hooks** | Responsive SPA with `useState`, `useEffect`, `useCallback`, `useMemo` | ✅ Complete |
| **9. Structured logging & debuggability**| Request ID tracking, timing middleware, structured logs | ✅ Complete |
| **10. Clear errors & sensible status codes** | `400`, `404`, `422`, `500`, `502` with standard JSON envelope | ✅ Complete |
| **11. Tradeoff awareness documentation** | Detailed sections on chunking, vector store, scaling, and production | ✅ Complete |
