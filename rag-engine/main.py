import os

# 必须在任何会间接导入 huggingface_hub 的库（sentence-transformers /
# transformers / langchain 等）之前设置 HF_ENDPOINT，否则国内访问
# huggingface.co 会报 SSL: WRONG_VERSION_NUMBER，镜像也不生效。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import json
from src.chunker import CascadeDocumentChunker
from src.retriever import HybridSearchRerankEngine

def main():
    # 1. 加载样例 Markdown 文档
    with open("data/raw/sample_doc.md", "r", encoding="utf-8") as f:
        sample_document = f.read()

    # 2. 结构化级联切片
    chunker = CascadeDocumentChunker(chunk_size=300, chunk_overlap=30)
    chunks = chunker.chunk(doc_id="tech_doc_001", content=sample_document)
    
    print(f"文档切片完成，共生成 {len(chunks)} 个切片：")
    for c in chunks:
        print(f" - ID: {c.chunk_id} | 标题 context: {c.metadata.section_heading} | 长度: {len(c.content)}")

    # 3. 初始化 RAG 引擎并建库
    engine = HybridSearchRerankEngine()
    engine.index_documents(chunks)

    # 4. 执行混合检索
    test_query = "专有名词和错误码查询不到怎么办？"
    print(f"\n[Search Demo] 执行 Query: '{test_query}'")
    results = engine.search(query=test_query, top_recall=10, top_final=3)
    
    for i, res in enumerate(results, 1):
        print(f"\n--- Top {i} (Rerank Score: {res.score:.4f}) [Chunk ID: {res.chunk_id}] ---")
        print(f"内容: {res.content}")

if __name__ == "__main__":
    main()
