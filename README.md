# AI Streaming Backend

基于 FastAPI 的高并发 LLM 流式(SSE)网关,异步转发上游 OpenAI 兼容接口的 token 流,具备客户端断连即时终止、自动 TraceID 注入与速率限制能力。

## 特性

- **异步非阻塞 I/O**:基于 `asyncio` + `httpx.AsyncClient` 零拷贝转发上游流式响应。
- **断连即停**:每个 chunk 都轮询 `request.is_disconnected()`,客户端取消时立即终止上游请求,节省 token 成本与连接资源。
- **TraceID 全链路追踪**:中间件自动生成或继承 `X-Trace-ID`,通过 `ContextVar` 在异步任务树中传播,Loguru 日志统一带上 `[TraceID: ...]`。
- **速率限制**:`slowapi` 默认 60 req/min/IP,超限返回 429。
- **类型安全**:Pydantic v2 端到端校验请求体。
- **OpenAI 兼容接口**:可对接任何 OpenAI 兼容上游(ModelScope / DeepSeek / SiliconFlow / OpenAI 等)。

## 目录结构

```
app/
├── main.py                 # FastAPI 入口、TraceID 中间件、限流器、生命周期
├── api/v1/chat.py          # SSE 端点 /api/v1/chat/completions
├── services/llm_service.py # 上游流式转发 + 断连守卫
├── schemas/chat.py         # Pydantic 请求模型
└── core/
    ├── config.py           # 环境变量配置
    └── logger.py           # Loguru + ContextVar 集成
```

## 快速开始

### 1. 安装依赖

推荐使用 `uv`(参见 `AGENT.md`):

```bash
uv venv
uv pip install -r requirements.txt
```

或使用 `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入上游信息:

```bash
cp .env.example .env
```

```dotenv
PROJECT_NAME="High-Performance AI Streaming Server"
VERSION="1.0.0"
LLM_API_BASE="https://api-inference.modelscope.cn/v1/"   # 末尾带不带 / 都可以
LLM_API_KEY="ms-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

> `llm_service.py` 会用 `LLM_API_BASE.rstrip('/')` 拼接 `/chat/completions`,因此末尾斜杠可省略。

### 3. 启动服务

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 验证

```bash
# 健康检查
curl -i http://localhost:8000/health

# SSE 流式测试(模型 ID 须与 LLM_API_BASE 对应的上游匹配)
curl -N -i -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3.5-35B-A3B",
    "messages": [{"role": "user", "content": "用一句话介绍人工智能。"}],
    "stream": true
  }'
```

## API 参考

### `POST /api/v1/chat/completions`

OpenAI 兼容的流式聊天接口。**仅支持 `stream=true`**。

**请求体**:

| 字段         | 类型                      | 必填 | 默认值                  | 说明                              |
| ------------ | ------------------------- | ---- | ----------------------- | --------------------------------- |
| `model`      | string                    | 否   | `Qwen/Qwen3.5-35B-A3B`  | 上游模型 ID,须匹配 `LLM_API_BASE` |
| `messages`   | List[{role, content}]     | 是   | -                       | `role` ∈ `system`/`user`/`assistant` |
| `temperature`| float                     | 否   | `0.7`                   | 范围 `[0.0, 2.0]`                  |
| `stream`     | bool                      | 是   | `true`                  | 必须为 `true`                     |

**响应**:`text/event-stream`,每个事件格式为 `data: {openai_chunk_json}\n\n`。

**响应头**:

- `X-Trace-ID`:本次请求的追踪 ID(可在请求头中传入以复用)。
- `Cache-Control: no-cache` / `Connection: keep-alive` / `X-Accel-Buffering: no`:防止反向代理缓冲 SSE。

### `GET /health`

返回 `{"status": "ok", "version": "1.0.0"}`。

## 架构

```text
[ Client ]
   │  POST /api/v1/chat/completions (stream=true)
   ▼
[ FastAPI ] ──► [ SlowAPI 60 req/min/IP ]
   │
   ├─► [ TraceID Middleware ] ──► ContextVar + X-Trace-ID
   ▼
[ Chat Router ]
   ▼
[ LLM Service ] ──► httpx.AsyncClient.stream("POST", upstream)
                      │   每收到一行:
                      │   1. 检查 request.is_disconnected()
                      │   2. 已断连 → break,释放上游连接
                      │   3. 未断连 → yield `data: ...\n\n`
                      ▼
                   [ Upstream LLM (OpenAI 兼容) ]
```

## Docker

```bash
docker build -t ai-streaming-backend .
docker run -p 8000:8000 --env-file .env ai-streaming-backend
```

镜像使用 `uvloop` + `httptools` 以获得更高吞吐。

## 常见问题

详见 [AGENT.md §5 Troubleshooting](./AGENT.md)。最典型的两类:

1. **`Upstream return status 404`**:`LLM_API_BASE` 配置错误,或模型 ID 与上游不匹配。本仓库已对末尾斜杠做了 `rstrip('/')` 容错。
2. **流式响应偶发卡顿**:通常是 Nginx 等反向代理缓冲所致,响应头已带 `X-Accel-Buffering: no`。

## 依赖

见 [requirements.txt](./requirements.txt):FastAPI 0.111、uvicorn 0.30、httpx 0.27、loguru 0.7、pydantic 2.7、pydantic-settings 2.3、slowapi 0.1.9。
