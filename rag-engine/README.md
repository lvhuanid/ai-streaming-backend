# Production-Grade Advanced RAG Engine

生产级高级 RAG（检索增强生成）引擎实现规范与核心代码。基于多策略文档切片、BM25 + Qdrant 向量双路召回、RRF 排序融合以及 BGE-Reranker 重排序机制，解决回答幻觉与漏检问题。

## 目录架构

```text
rag-engine/
├── config/
│   └── settings.py             # 全局配置参数
├── data/
│   ├── raw/
│   │   └── sample_doc.md       # 原始样例文档
│   └── eval_dataset.json       # Hit@K 测试数据集
├── src/
│   ├── __init__.py
│   ├── models.py               # Pydantic 数据模型定义
│   ├── chunker.py              # 多策略级联切片器
│   └── retriever.py            # BM25 + Qdrant + RRF + BGE-Reranker 核心引擎
├── tests/
│   ├── __init__.py
│   └── test_evaluation.py      # Hit@K 评估脚本
├── .gitignore
├── main.py                     # 主运行入口
├── README.md
└── requirements.txt            # 项目依赖
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行 Demo

```bash
python main.py
```

### 3. 运行 Hit@K 评估

```bash
python -m tests.test_evaluation
```
