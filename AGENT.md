# AGENT.md - AI Agent Architecture & Developer Guide

This document defines the agent architecture, system patterns, and integration guidelines for **MVP 1: High-Concurrency AI SSE Backend**.

---

## 1. Executive Summary & Design Goals

The primary objective of this repository is to provide a production-grade, asynchronous backend for streaming LLM (Large Language Model) tokens efficiently. 

### Key Principles
* **Non-Blocking I/O (`asyncio`)**: Leverage Python's asynchronous event loop to handle thousands of concurrent SSE connections with low resource consumption.
* **Aggressive Disconnect Handling**: Immediate termination of upstream LLM requests when the client cancels or disconnects, saving API token costs and releasing sockets.
* **Full Observability (Tracing & Context)**: Automatic trace ID propagation using `ContextVars` across async task contexts.
* **Strict Type Safety**: End-to-end Pydantic schema validation for requests and responses.

---

## 2. System Architecture

```text
[ Client / Frontend ]
       │
       │ HTTP POST /api/v1/chat/completions (stream=true)
       ▼
[ FastAPI Gateway ] ──► [ SlowAPI Rate Limiter ] (60 req/min/IP)
       │
       ├─► [ TraceID Middleware ] ──► Injects X-Trace-ID into ContextVars & Headers
       │
       ▼
[ Chat Router (`chat.py`) ]
       │
       ▼
[ LLM Service (`llm_service.py`) ]
       │
       ├──► [ httpx.AsyncClient ] ──► POST Stream to Upstream LLM (DeepSeek / Qwen / OpenAI)
       │                                     │
       │─── (Polling `request.is_disconnected()`) ◄──┘
       │          │
       │          ├── [If Client Connected] ──► Yield `data: {...}\n\n` (SSE)
       │          └── [If Client Disconnected] ──► Break stream loop & abort httpx request
```

---

## 3. Core Component Breakdown

### 3.1 Trace ID Middleware (`app/main.py`)
- **Purpose**: Generates or extracts `X-Trace-ID` and stores it in a `contextvars.ContextVar`.
- **Mechanism**: Guarantees that all log statements printed via `Loguru` within the same async request execution tree automatically include `[TraceID: <uuid>]`.

### 3.2 SSE Generator & Disconnect Guard (`app/services/llm_service.py`)
- **Upstream Engine**: Uses `httpx.AsyncClient` with `client.stream("POST", ...)` for zero-copy streaming.
- **Cancellation Check**: On every chunk received from upstream, `await request.is_disconnected()` is checked.
- **Yield Loop Yielding**: Calls `await asyncio.sleep(0)` after yielding each event chunk. This yields event loop control back to FastAPI's connection monitor to immediately trigger disconnect flags.

### 3.3 Rate Limiter (`app/api/v1/chat.py`)
- **Engine**: `slowapi` wrapping `limits`.
- **Default Policy**: 60 requests per minute per IP address. Excess requests receive HTTP 429.

---

## 4. Agent Tooling & Execution Environment

When operating inside or extending this repository as an Autonomous Code Agent:

### 4.1 Preferred Package Manager
Always use **`uv`** for dependency management, virtual environments, and execution:
```bash
# Create venv and install dependencies
uv venv
uv pip install -r requirements.txt

# Run server with live reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4.2 Key File Locations
| Path | Description |
| :--- | :--- |
| `app/main.py` | FastAPI instantiation, lifespan hooks, rate limiter setup, and trace ID middleware. |
| `app/api/v1/chat.py` | SSE Endpoint (`/api/v1/chat/completions`). |
| `app/services/llm_service.py` | Upstream LLM stream handler with `is_disconnected()` logic. |
| `app/core/config.py` | Environment variable schema (`LLM_API_BASE`, `LLM_API_KEY`). |
| `app/core/logger.py` | Loguru integration with `ContextVar` trace filtering. |
| `app/schemas/chat.py` | Pydantic model for chat completion payloads. |

---

## 5. Troubleshooting Common Issues

### 5.1 Upstream 404 Error (`Upstream return status 404`)
- **Cause 1 — Trailing slash in `LLM_API_BASE`**: When `.env` sets a base URL ending with `/` (e.g. `https://api-inference.modelscope.cn/v1/`), naive concatenation with `/chat/completions` produces a double slash (`.../v1//chat/completions`), which strict routers (ModelScope, DeepSeek, etc.) reject with 404.
  - **Fix (already applied)**: `llm_service.py` now strips the trailing slash via `settings.LLM_API_BASE.rstrip('/')` before appending `/chat/completions`, so both `…/v1` and `…/v1/` work.
- **Cause 2 — Wrong model name**: Model ID must match an OpenAI-compatible model on the upstream provider (e.g. `Qwen/Qwen3.5-35B-A3B` on ModelScope, `deepseek-chat` on DeepSeek).
- **Verification**: Check that `LLM_API_BASE` points to a valid OpenAI-compatible base URL (e.g. `https://api-inference.modelscope.cn/v1/` or `https://api.deepseek.com/v1`) and that the model ID is supported by that provider.

### 5.2 Stream Not Yielding Intermittently
- **Cause**: Nginx or reverse proxy buffering SSE responses.
- **Fix**: Ensure response headers contain `X-Accel-Buffering: no` and `Cache-Control: no-cache` (already set in `chat.py`).

---

## 6. Verification & Automated Testing Commands

To test stream integrity and verify disconnect behavior:

```bash
# 1. Health check
curl -i http://localhost:8000/health

# 2. SSE Stream Test (model must match a model ID supported by LLM_API_BASE in .env)
curl -N -i -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen3.5-35B-A3B", "messages": [{"role": "user", "content": "Hello"}], "stream": true}'

# 3. Disconnect Test
# Run the command above with a long prompt, then press Ctrl+C midway.
# Verify that the server log shows:
# "Client connection disconnected! Terminating upstream stream immediately."
```
