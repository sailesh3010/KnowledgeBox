import re
from typing import List, Dict, Any
from app.core.config import get_settings


class Chunk:
    def __init__(self, index: int, content: str, char_start: int, char_end: int):
        self.index = index
        self.content = content.strip()
        self.char_start = char_start
        self.char_end = char_end

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_index": self.index,
            "content": self.content,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "char_count": len(self.content),
            "word_count": len(self.content.split()),
        }


class IntentionalChunker:
    """
    Recursive Semantic Boundary Chunker.
    Splits text hierarchically on paragraph, sentence, and word boundaries
    to preserve semantic integrity while honoring target chunk size and overlap.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = min(chunk_overlap, chunk_size // 2)

    def chunk_text(self, text: str) -> List[Chunk]:
        """Split raw text into structured overlapping chunks with character offsets."""
        text_clean = text.strip()
        if not text_clean:
            return []

        # If text is already smaller than or equal to chunk size, return single chunk
        if len(text_clean) <= self.chunk_size:
            return [Chunk(index=0, content=text_clean, char_start=0, char_end=len(text_clean))]

        # Recursive splitting separators in order of semantic preservation
        separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]
        raw_pieces = self._split_recursive(text_clean, separators, self.chunk_size)

        # Merge pieces into chunks of target size with sliding overlap
        chunks: List[Chunk] = []
        current_chunk_text = ""
        current_start_offset = 0
        search_cursor = 0

        for piece in raw_pieces:
            piece_str = piece.strip()
            if not piece_str:
                continue

            if not current_chunk_text:
                current_chunk_text = piece_str
                # Locate start offset in original text
                pos = text_clean.find(piece_str, search_cursor)
                if pos != -1:
                    current_start_offset = pos
                    search_cursor = pos
            elif len(current_chunk_text) + len(piece_str) + 1 <= self.chunk_size:
                current_chunk_text += " " + piece_str
            else:
                # Commit current chunk
                end_offset = current_start_offset + len(current_chunk_text)
                chunks.append(Chunk(
                    index=len(chunks),
                    content=current_chunk_text,
                    char_start=current_start_offset,
                    char_end=end_offset
                ))

                # Compute overlapping carryover
                overlap_text = self._compute_overlap(current_chunk_text, self.chunk_overlap)
                if overlap_text:
                    current_chunk_text = overlap_text + " " + piece_str
                    pos = text_clean.find(overlap_text, current_start_offset)
                    current_start_offset = pos if pos != -1 else search_cursor
                else:
                    current_chunk_text = piece_str
                    pos = text_clean.find(piece_str, search_cursor)
                    current_start_offset = pos if pos != -1 else search_cursor

                search_cursor = current_start_offset

        # Commit trailing chunk
        if current_chunk_text:
            end_offset = current_start_offset + len(current_chunk_text)
            chunks.append(Chunk(
                index=len(chunks),
                content=current_chunk_text,
                char_start=current_start_offset,
                char_end=min(end_offset, len(text_clean))
            ))

        return chunks

    def _split_recursive(self, text: str, separators: List[str], max_size: int) -> List[str]:
        """Recursively break text down using progressively smaller separators."""
        if len(text) <= max_size or not separators:
            # Base case: text fits or no more separators
            if len(text) <= max_size:
                return [text]
            # Hard break if single word is longer than max_size
            return [text[i:i + max_size] for i in range(0, len(text), max_size)]

        sep = separators[0]
        remaining_seps = separators[1:]

        parts = text.split(sep)
        result: List[str] = []

        for i, part in enumerate(parts):
            # Reattach separator (except at end)
            token = part + (sep if i < len(parts) - 1 else "")
            if len(token) <= max_size:
                result.append(token)
            else:
                # Recurse with finer separator
                sub_parts = self._split_recursive(token, remaining_seps, max_size)
                result.extend(sub_parts)

        return result

    def _compute_overlap(self, text: str, target_overlap: int) -> str:
        """Find a clean word or sentence boundary near target_overlap from the end."""
        if len(text) <= target_overlap:
            return ""

        tail = text[-target_overlap:]
        # Find first whitespace or sentence boundary in the tail
        match = re.search(r"[\s.?!]", tail)
        if match:
            clean_tail = tail[match.end():].strip()
            if clean_tail:
                return clean_tail

        return tail.strip()


def get_chunker() -> IntentionalChunker:
    settings = get_settings()
    return IntentionalChunker(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
