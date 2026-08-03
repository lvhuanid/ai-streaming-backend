从这个工程化的 Advanced RAG 项目中，你可以学到核心的 RAG 进阶架构思想，并能在多个维度上对它进行生产级的扩展。

---

## 1. 从本项目中可以学到什么？

### ① 架构设计：从“粗召回”到“精重排”的两阶段范式

* **避免盲目依赖 Vector Search**：单靠向量检索在处理专有名词、特定错误码或特定产品型号时极易漏检或幻觉。
* **分工明确的检索 Pipeline**：
* **第一阶段（粗召回）**：侧重**高召回率（Recall）**。通过 BM25（语法词频）与 Dense Vector（语义向量）双路并行，筛选出 Top-20 或 Top-40 候选集。


* **第二阶段（精重排）**：侧重**高精准度（Precision）**。使用 Cross-Encoder 计算 Query 与 Candidate 的交叉注意力（Cross-Attention）打分，消除双塔向量模型带来的信息损耗，精准抓取 Top-3。





### ② 文档处理：结构优先的级联切片 (Cascade Chunking)

* **解决切片截断问题**：传统的固定长度切片（Fixed-size Chunking）容易将代码块或关联段落割裂。
* **利用 Markdown 元数据注入**：先利用 Markdown 标题层级（`#`, `##`, `###`）提取章节元数据并保留，再针对超长文本进行字符/标点级别的递归次级切片（`\n\n`, `\n`, `。`），最大程度保障上下文完整性。



### ③ 融合算法：无量纲化的 RRF (Reciprocal Rank Fusion)

* **解决异构打分难以直接相加的问题**：BM25 输出的是非有界绝对词频分值，而向量数据库输出的是 $[0, 1]$ 的余弦相似度，两者无法直接用 `0.5 * score1 + 0.5 * score2` 融合。
* **基于排名的无参融合**：学习并应用公式 $RRF\_Score(d) = \sum \frac{1}{k + r(d)}$，只依赖文档在各检索路中的名次（Rank）进行公平评分与融合。



### ④ 工程落地的类型安全与评测意识

* **Pydantic 类型强约束**：通过统一定义 `DocumentChunk`、`SearchResult` 等传输层对象，规范数据在解析、建库、检索间的流转。


* **数据驱动的指标评测**：不凭感觉调优，而是建立了基于真实 Ground Truth 的 **Hit@K** 命中率自动化评测脚本，实现量化迭代。



---

## 2. 这个项目后续可以怎么扩展？

如果你希望把这个项目升级为能够支撑**千万级数据量、高并发、复杂业务场景**的商业级 RAG 系统，可以从以下四个方向扩展：

### ① 检索层下推与海量规模支持 (Native Sparse)

* **当前情况**：目前 BM25 索引运行在 Python 进程内存中，难以应对超大规模数据。


* **扩展方案**：
* **Qdrant Native Hybrid Search**：使用 **SPLADE** 或 **BGE-M3** 提取稀疏向量（Sparse Vector），将关键词/稀疏检索与密集向量统一存储在 Qdrant 中。
* 这样可以利用 Qdrant 自身的离线/集群索引能力，避免 Python 端维护独立 BM25 实例的内存瓶颈。



### ② Query 理解与前置增强 (Query Processing)

* **Query Rewriting（查询重写）**：在进入检索前，利用 LLM 将用户大白话改写为更贴近文档库风格的技术短语。
* **HyDE (Hypothetical Document Embeddings)**：先让 LLM 生成一份“假设性正确回答”，再拿这份假回答去检索真实文档，大幅提升语义相似度。
* **Query Decomposition（复杂问题拆解）**：将复合型问题（如“比较 Qdrant 和 Milvus 在混合检索上的异同”）拆解为多个子 Query 分别检索再合并。

### ③ Context 动态压缩与二度降噪 (Context Compression)

* **当前情况**：Top-3 召回的完整 Chunk 放入 Prompt 仍可能包含较多无关废话，浪费 LLM 窗口且引发丢失在中间（Lost in the Middle）现象。
* **扩展方案**：
* **Sentence-level Compressor**：在 Rerank 之后，利用 LLM 或小模型按句子粒度提取与 Query 最相关的 1-2 句话，过滤掉无关段落后再拼接 Prompt。



### ④ 数据源拓展与多模态解析 (Multi-modal Parser)

* **当前情况**：当前仅支持纯文本/Markdown 格式。


* **扩展方案**：
* 引入 `Unstructured` 或 `Nougat` / `PaddleOCR` 解析器，支持 PDF、Word、PPT 以及扫描件中的**表格提取（Table Parsing）**与**图片（OCR / Captioning）**，实现多模态文档接入。