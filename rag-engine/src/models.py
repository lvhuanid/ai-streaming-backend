from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChunkMetadata(BaseModel):
    doc_id: str
    chunk_id: str
    section_heading: Optional[str] = None
    start_char_idx: int = 0
    end_char_idx: int = 0
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)

class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None

class SearchResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: ChunkMetadata
    source: str  # "bm25", "vector", "hybrid_rerank"
