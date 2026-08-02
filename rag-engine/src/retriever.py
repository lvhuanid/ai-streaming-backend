import jieba
import numpy as np
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from src.models import DocumentChunk, SearchResult
# 必须在 sentence_transformers 之前导入，以便 config.settings 设置 HF_ENDPOINT 镜像
from config.settings import settings
from sentence_transformers import SentenceTransformer, CrossEncoder

def chinese_tokenizer(text: str) -> List[str]:
    """使用 jieba 进行中文精确分词并去空，提升 BM25 词频统计精准度"""
    return [word.strip().lower() for word in jieba.lcut(text) if word.strip()]

class HybridSearchRerankEngine:
    def __init__(
        self, 
        collection_name: str = settings.COLLECTION_NAME,
        dense_model_name: str = settings.DENSE_MODEL_NAME,
        rerank_model_name: str = settings.RERANK_MODEL_NAME
    ):
        print(f"[Init] 正在加载 Dense Embedding 模型: {dense_model_name}...")
        self.embedding_model = SentenceTransformer(dense_model_name)
        self.vector_dim = self.embedding_model.get_sentence_embedding_dimension()

        print(f"[Init] 正在加载 Reranker 模型: {rerank_model_name}...")
        self.reranker = CrossEncoder(rerank_model_name, max_length=512)

        # 初始化 Qdrant 客户端
        self.client = QdrantClient(settings.QDRANT_HOST)
        self.collection_name = collection_name
        
        self.bm25: Optional[BM25Okapi] = None
        self.chunks_repo: Dict[str, DocumentChunk] = {}
        self.chunk_id_list: List[str] = []
        
        self._init_qdrant()

    def _init_qdrant(self):
        """初始化或重建 Qdrant Collection"""
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_dim, distance=Distance.COSINE)
        )

    def encode_texts(self, texts: List[str]) -> List[List[float]]:
        """批量向量化文本"""
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return embeddings.tolist()

    def index_documents(self, chunks: List[DocumentChunk]):
        """建库：同步构建 BM25 索引与 Qdrant 向量索引"""
        if not chunks:
            return

        print(f"[Index] 开始索引 {len(chunks)} 个文档块...")
        corpus_tokens = []
        points = []
        
        # 1. 生成所有文本的 Dense Embedding
        contents = [chunk.content for chunk in chunks]
        embeddings = self.encode_texts(contents)

        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk.embedding = emb
            self.chunks_repo[chunk.chunk_id] = chunk
            self.chunk_id_list.append(chunk.chunk_id)

            # 2. BM25 中文分词语料
            tokens = chinese_tokenizer(chunk.content)
            corpus_tokens.append(tokens)

            # 3. 构造 Qdrant Vector Points
            points.append(PointStruct(
                id=idx,
                vector=emb,
                payload={"chunk_id": chunk.chunk_id, "content": chunk.content}
            ))

        # 4. 实例化 BM25 引擎与批量写入 Qdrant
        self.bm25 = BM25Okapi(corpus_tokens)
        self.client.upsert(collection_name=self.collection_name, points=points)
        print("[Index] 索引构建完成！")

    def _rrf(self, bm25_cids: List[str], vector_cids: List[str], k: int = settings.RRF_K) -> List[str]:
        """Reciprocal Rank Fusion 融合算法"""
        scores: Dict[str, float] = {}

        for rank, cid in enumerate(bm25_cids):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        for rank, cid in enumerate(vector_cids):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)

        sorted_cids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return sorted_cids

    def search(
        self, 
        query: str, 
        top_recall: int = settings.TOP_RECALL, 
        top_final: int = settings.TOP_FINAL
    ) -> List[SearchResult]:
        """双路召回 + RRF 融合 + Cross-Encoder 精重排"""
        if not self.bm25:
            raise ValueError("索引为空，请先调用 index_documents() 建立索引。")

        # Step 1: BM25 语法关键词检索
        query_tokens = chinese_tokenizer(query)
        bm25_scores = self.bm25.get_scores(query_tokens)
        top_bm25_indices = np.argsort(bm25_scores)[::-1][:top_recall]
        bm25_cids = [self.chunk_id_list[i] for i in top_bm25_indices]

        # Step 2: Qdrant 语义向量检索
        # qdrant-client >=1.10 移除了 client.search(),改用 query_points()
        query_vector = self.encode_texts([query])[0]
        qdrant_response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_recall
        )
        vector_cids = [point.payload["chunk_id"] for point in qdrant_response.points]

        # Step 3: RRF 融合计算
        fused_cids = self._rrf(bm25_cids, vector_cids)[:top_recall * 2]
        candidate_chunks = [self.chunks_repo[cid] for cid in fused_cids]

        if not candidate_chunks:
            return []

        # Step 4: BGE-Reranker 对候选文本对重打分
        pair_inputs = [[query, chunk.content] for chunk in candidate_chunks]
        rerank_scores = self.reranker.predict(pair_inputs)

        # 打分整合与降序截取 Top-K
        scored_results: List[SearchResult] = []
        for chunk, score in zip(candidate_chunks, rerank_scores):
            scored_results.append(SearchResult(
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                score=float(score),
                metadata=chunk.metadata,
                source="hybrid_rerank"
            ))

        scored_results.sort(key=lambda x: x.score, reverse=True)
        return scored_results[:top_final]
