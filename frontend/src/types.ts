export type SourceType = 'note' | 'url';

export interface ItemSummary {
  id: string;
  source_type: SourceType;
  title: string;
  url?: string;
  content_preview: string;
  char_count: number;
  word_count: number;
  chunk_count: number;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface ChunkPreview {
  id: string;
  chunk_index: number;
  char_start: number;
  char_end: number;
  content: string;
  created_at: string;
}

export interface ItemDetail extends ItemSummary {
  raw_content: string;
  chunks: ChunkPreview[];
}

export interface SourceCitation {
  item_id: string;
  chunk_id: string;
  source_title: string;
  source_type: SourceType;
  url?: string;
  chunk_index: number;
  snippet: string;
  similarity_score: number;
}

export interface QueryResponse {
  query: string;
  answer: string;
  sources: SourceCitation[];
  retrieval_count: number;
  provider: string;
  model: string;
  latency_ms: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  provider: string;
  active_embedding_model: string;
  active_chat_model: string;
  items_count: number;
  chunks_count: number;
  database_path: string;
}
