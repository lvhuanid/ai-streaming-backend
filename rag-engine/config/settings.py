import os

# 使用 HuggingFace 国内镜像，解决 huggingface.co 访问失败
# (SSL: WRONG_VERSION_NUMBER) 问题。必须在 sentence-transformers /
# huggingface_hub 被导入前设置才生效。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from pydantic import BaseModel

class Settings(BaseModel):
    # Model Configurations
    DENSE_MODEL_NAME: str = "BAAI/bge-large-zh-v1.5"
    RERANK_MODEL_NAME: str = "BAAI/bge-reranker-base"
    
    # Chunking Configurations
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    
    # Retrieval Configurations
    TOP_RECALL: int = 20
    TOP_FINAL: int = 3
    RRF_K: int = 60
    
    # Qdrant Configurations
    QDRANT_HOST: str = ":memory:"
    COLLECTION_NAME: str = "production_rag"

settings = Settings()
