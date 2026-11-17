import time
import re
from typing import List, Dict, Any, Tuple
from app.core.config import get_settings
from app.core.logging import logger
from app.core.errors import ProviderError
from app.services.embedder import get_embedder
from app.services.vector_store import vector_store, VectorSearchResult


class RAGService:
    """End-to-end RAG orchestrator: query embedding -> vector retrieval -> prompt assembly -> LLM generation with citations."""

    SYSTEM_PROMPT = (
        "You are an intelligent knowledge assistant for Turium's 'AI Knowledge Inbox'.\n"
        "Your role is to provide accurate, concise, and helpful answers to the user's question "
        "strictly based on their saved notes and web articles.\n\n"
        "Rules:\n"
        "1. GROUNDING: Rely only on the provided context snippets. Do not hallucinate or speculate.\n"
        "2. CITATIONS: Attribute facts by citing the source index in square brackets, e.g. [Source 1], [Source 2].\n"
        "3. UNCERTAINTY: If the provided context does not contain enough information to answer the question, "
        "state: 'Based on your saved notes and articles, I don't have enough information to answer this question.'\n"
        "4. STYLE: Use clean Markdown formatting."
    )

    def __init__(self):
        self.settings = get_settings()

    async def answer_query(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Execute full RAG pipeline:
        1. Embed user query
        2. Retrieve top-k relevant chunks from SQLite vector store
        3. Format grounded prompt with cited source blocks
        4. Query LLM (OpenAI, Gemini, or Local Synthesizer)
        5. Return answer with full cited sources and latency metrics
        """
        start_time = time.perf_counter()

        embedder = get_embedder()
        query_vector = await embedder.embed_query(query)

        # Retrieve relevant chunks from vector store
        results: List[VectorSearchResult] = vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
            min_score=min_score,
        )

        sources = [r.to_dict() for r in results]

        # If no relevant chunks found in database
        if not results:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "query": query,
                "answer": "No relevant notes or articles were found in your knowledge inbox matching this query. Try ingesting some content first or adjusting your search terms.",
                "sources": [],
                "retrieval_count": 0,
                "provider": embedder.provider_name,
                "model": "none",
                "latency_ms": round(latency_ms, 2),
            }

        # Build context prompt
        context_blocks = []
        for idx, r in enumerate(results, 1):
            source_header = f"[Source {idx}] Title: {r.source_title} ({r.source_type.upper()})"
            if r.url:
                source_header += f" - {r.url}"
            context_blocks.append(f"{source_header}\nExcerpt:\n\"{r.content}\"")

        context_str = "\n\n---\n\n".join(context_blocks)
        user_prompt = f"Context:\n{context_str}\n\nQuestion: {query}\n\nAnswer:"

        # Call LLM
        provider = self.settings.resolve_provider()
        answer, model_used = await self._generate_answer(provider, user_prompt, results)

        latency_ms = (time.perf_counter() - start_time) * 1000

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "retrieval_count": len(results),
            "provider": provider,
            "model": model_used,
            "latency_ms": round(latency_ms, 2),
        }

    async def _generate_answer(
        self,
        provider: str,
        user_prompt: str,
        chunks: List[VectorSearchResult],
    ) -> Tuple[str, str]:
        """Dispatch generation to the active provider."""
        if provider == "openai" and self.settings.OPENAI_API_KEY:
            return await self._generate_openai(user_prompt)

        if provider == "gemini" and self.settings.GEMINI_API_KEY:
            return await self._generate_gemini(user_prompt)

        # Local fallback mode
        return self._generate_local(user_prompt, chunks)

    async def _generate_openai(self, prompt: str) -> Tuple[str, str]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        model = self.settings.OPENAI_CHAT_MODEL
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=800,
            )
            answer = response.choices[0].message.content or ""
            return answer.strip(), model
        except Exception as e:
            logger.error(f"OpenAI chat completion error: {str(e)}")
            raise ProviderError(
                message=f"OpenAI generation failed: {str(e)}",
                details={"model": model, "error": str(e)},
            )

    async def _generate_gemini(self, prompt: str) -> Tuple[str, str]:
        from google import genai
        client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
        model = self.settings.GEMINI_CHAT_MODEL
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}"

        # Attempt with configured model, with automatic fallback to high-availability flash models
        candidate_models = [model]
        for fallback in ["gemini-3-flash-preview", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_error = None
        for m in candidate_models:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=full_prompt,
                )
                text = (response.text or "").strip()
                return text, m
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini model '{m}' call failed ({str(e)}). Checking alternate models if available...")
                continue

        logger.error(f"Gemini generation error on all candidate models: {str(last_error)}")
        raise ProviderError(
            message=f"Gemini generation failed: {str(last_error)}",
            details={"model": model, "error": str(last_error)},
        )

    def _generate_local(
        self,
        prompt: str,
        chunks: List[VectorSearchResult],
    ) -> Tuple[str, str]:
        """
        Extractive RAG synthesizer for offline/fallback mode.
        Constructs a structured answer citing sources directly from the retrieved snippets.
        """
        if not chunks:
            return "No matching content available.", "local-synthesizer"

        lines = [
            "Here is the relevant information retrieved from your saved content:",
            ""
        ]
        for idx, chunk in enumerate(chunks[:3], 1):
            sentences = [s.strip() for s in re.split(r"[.!?]\s+", chunk.content) if len(s.strip()) > 15]
            summary_snippet = " ".join(sentences[:2]) if sentences else chunk.content[:200]
            lines.append(f"- **{chunk.source_title}** [Source {idx}]: {summary_snippet}")

        lines.append("\n*(Generated via Local Synthesizer. Set `OPENAI_API_KEY` or `GEMINI_API_KEY` in `.env` for generative LLM synthesis.)*")
        return "\n".join(lines), "local-extractive-synthesizer"


rag_service = RAGService()
