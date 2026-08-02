# Qdrant 与混合检索架构指南

## 向量数据库配置
Qdrant 是一个高并发的开源向量数据库，专为高维向量检索（ANN）设计。生产环境中支持 Cosine、Dot Product 和 Euclidean 距离度量标准。对于超过千万级的海量数据集，可以启用 HNSW 索引架构来降低查询延迟。

## BM25 专有名词精准匹配
在传统检索中，Embedding 常常无法准确处理专有名词、特定错误码（例如 ERR_502_BAD_GATEWAY）或特定产品型号。BM25 基于词频（TF-IDF 演进）算法，能够极大地提升这类精确关键词的抓取能力。

## BGE 重排序引擎
Cross-Encoder 模型（如 BGE-Reranker-Large）通过将 Query 和 Document 同时输入模型进行交叉注意力（Cross-Attention）计算，能消除双塔向量模型带来的信息损失，准确筛选出最契合的 Top-3 文本片段插入 Context。
