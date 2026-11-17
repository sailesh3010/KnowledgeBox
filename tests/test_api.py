import pytest
from unittest.mock import patch, AsyncMock


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "provider" in data
    assert "items_count" in data


def test_ingest_note_success(client):
    payload = {
        "type": "note",
        "title": "Machine Learning Fundamentals",
        "content": "Supervised learning uses labeled training datasets to train algorithms that classify data or predict outcomes accurately.",
        "metadata": {"category": "ai"}
    }
    response = client.post("/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Machine Learning Fundamentals"
    assert data["source_type"] == "note"
    assert data["chunk_count"] >= 1
    assert "id" in data

    # Verify item appears in /items
    list_resp = client.get("/items")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == data["id"]


def test_ingest_url_mocked(client):
    mock_html = """
    <html>
        <head><title>Cloud Native Architecture</title></head>
        <body>
            <p>Cloud-native technologies empower organizations to build scalable applications in modern environments.</p>
        </body>
    </html>
    """
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = mock_html
    mock_response.url = "https://cloud.example.com/native"

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        payload = {
            "type": "url",
            "content": "https://cloud.example.com/native",
        }
        response = client.post("/ingest", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["source_type"] == "url"
        assert data["title"] == "Cloud Native Architecture"
        assert data["url"] == "https://cloud.example.com/native"


def test_ingest_validation_failure(client):
    # Empty content
    response = client.post("/ingest", json={"type": "note", "content": "   "})
    assert response.status_code == 422

    # Invalid URL format
    response2 = client.post("/ingest", json={"type": "url", "content": "not-a-valid-url"})
    assert response2.status_code == 422


def test_query_knowledge_inbox(client):
    # Ingest a sample note
    note = {
        "type": "note",
        "title": "FastAPI Architecture",
        "content": "FastAPI is a modern, fast Python web framework based on standard Python type hints and Starlette.",
    }
    client.post("/ingest", json=note)

    # Query with relevant question
    query_payload = {
        "query": "What is FastAPI based on?",
        "top_k": 3,
        "min_score": 0.01,
    }
    response = client.post("/query", json=query_payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["source_title"] == "FastAPI Architecture"
    assert data["sources"][0]["similarity_score"] > 0


def test_query_empty_knowledge_base(client):
    query_payload = {
        "query": "Where is my data?",
        "top_k": 3,
    }
    response = client.post("/query", json=query_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["retrieval_count"] == 0
    assert "No relevant notes or articles were found" in data["answer"]


def test_delete_item(client):
    # Ingest item
    note = {
        "type": "note",
        "title": "Temporary Note",
        "content": "This note will be deleted shortly.",
    }
    resp = client.post("/ingest", json=note)
    item_id = resp.json()["id"]

    # Delete
    del_resp = client.delete(f"/items/{item_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    # Check that item is gone
    get_resp = client.get(f"/items/{item_id}")
    assert get_resp.status_code == 404
