import json
import time
from typing import List, Dict
from src.chunker import CascadeDocumentChunker
from src.retriever import HybridSearchRerankEngine

def run_hit_at_k_evaluation(
    engine: HybridSearchRerankEngine, 
    test_dataset: List[Dict[str, str]], 
    k_values: List[int] = [1, 3, 5]
) -> Dict[str, float]:
    hit_counts = {k: 0 for k in k_values}
    total_queries = len(test_dataset)

    print(f"\n================ [Evaluation Start] ================")
    print(f"评估数据集总量: {total_queries} 条 Query")
    start_time = time.time()

    for item in test_dataset:
        query = item["query"]
        target_id = item["expected_chunk_id"]
        
        max_k = max(k_values)
        search_results = engine.search(query=query, top_recall=20, top_final=max_k)
        retrieved_ids = [res.chunk_id for res in search_results]

        for k in k_values:
            if target_id in retrieved_ids[:k]:
                hit_counts[k] += 1

    metrics = {f"Hit@{k}": round(hit_counts[k] / total_queries, 4) for k in k_values}
    
    print(f"评估耗时: {time.time() - start_time:.3f} 秒")
    print(f"测试结果评估指标: {metrics}")
    print(f"===================================================\n")
    return metrics

if __name__ == "__main__":
    # 读取样例数据与评测集
    with open("data/raw/sample_doc.md", "r", encoding="utf-8") as f:
        doc_text = f.read()
        
    with open("data/eval_dataset.json", "r", encoding="utf-8") as f:
        eval_dataset = json.load(f)

    chunker = CascadeDocumentChunker(chunk_size=300, chunk_overlap=30)
    chunks = chunker.chunk(doc_id="tech_doc_001", content=doc_text)

    engine = HybridSearchRerankEngine()
    engine.index_documents(chunks)

    run_hit_at_k_evaluation(engine, eval_dataset, k_values=[1, 3])
