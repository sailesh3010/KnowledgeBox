import sqlite3
import json
import os
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from app.core.config import get_settings
from app.core.logging import logger


class Database:
    """Thread-safe SQLite database manager for items and vector chunks."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_settings().DATABASE_PATH
        self._init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")  # High concurrency WAL mode
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema with items and chunks tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    raw_content TEXT NOT NULL,
                    content_preview TEXT NOT NULL,
                    char_count INTEGER NOT NULL,
                    word_count INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
            """)

            # Chunks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    char_start INTEGER NOT NULL,
                    char_end INTEGER NOT NULL,
                    embedding TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
                );
            """)

            # Performance indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_item_id ON chunks(item_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_created_at ON items(created_at DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_source_type ON items(source_type);")

        logger.info(f"Database initialized at: {os.path.abspath(self.db_path)}")

    # ==========================
    # Item Operations
    # ==========================

    def insert_item(
        self,
        item_id: str,
        source_type: str,
        title: str,
        raw_content: str,
        content_preview: str,
        char_count: int,
        word_count: int,
        chunk_count: int,
        created_at: str,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        metadata_json = json.dumps(metadata or {})
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO items (
                    id, source_type, title, url, raw_content, content_preview,
                    char_count, word_count, chunk_count, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id, source_type, title, url, raw_content, content_preview,
                    char_count, word_count, chunk_count, created_at, metadata_json
                )
            )

    def list_items(self, limit: int = 100, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM items")
            total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT id, source_type, title, url, content_preview,
                       char_count, word_count, chunk_count, created_at, metadata_json
                FROM items
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            rows = cursor.fetchall()
            items = []
            for row in rows:
                item_dict = dict(row)
                item_dict["metadata"] = json.loads(item_dict.pop("metadata_json") or "{}")
                items.append(item_dict)
            return items, total

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, source_type, title, url, raw_content, content_preview,
                       char_count, word_count, chunk_count, created_at, metadata_json
                FROM items
                WHERE id = ?
                """,
                (item_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")

            cursor.execute(
                """
                SELECT id, chunk_index, char_start, char_end, content, created_at
                FROM chunks
                WHERE item_id = ?
                ORDER BY chunk_index ASC
                """,
                (item_id,)
            )
            item["chunks"] = [dict(c) for c in cursor.fetchall()]
            return item

    def delete_item(self, item_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    # ==========================
    # Chunk & Vector Operations
    # ==========================

    def insert_chunks(self, chunks_data: List[Dict[str, Any]]) -> None:
        """Bulk insert chunks with embeddings."""
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO chunks (
                    id, item_id, chunk_index, content, char_start, char_end, embedding, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        c["id"],
                        c["item_id"],
                        c["chunk_index"],
                        c["content"],
                        c["char_start"],
                        c["char_end"],
                        json.dumps(c["embedding"]),
                        c["created_at"]
                    )
                    for c in chunks_data
                ]
            )

    def get_all_chunks_with_embeddings(self) -> List[Dict[str, Any]]:
        """Retrieve all stored chunks joined with parent item metadata for vector search."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.id AS chunk_id, c.item_id, c.chunk_index, c.content, c.embedding,
                       i.title AS source_title, i.source_type, i.url
                FROM chunks c
                JOIN items i ON c.item_id = i.id
                """
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "chunk_id": r["chunk_id"],
                    "item_id": r["item_id"],
                    "chunk_index": r["chunk_index"],
                    "content": r["content"],
                    "embedding": json.loads(r["embedding"]),
                    "source_title": r["source_title"],
                    "source_type": r["source_type"],
                    "url": r["url"]
                })
            return results

    def get_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM items")
            items_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM chunks")
            chunks_count = cursor.fetchone()[0]
            return {
                "items_count": items_count,
                "chunks_count": chunks_count,
                "db_path": os.path.abspath(self.db_path)
            }


# Singleton database instance
db = Database()
