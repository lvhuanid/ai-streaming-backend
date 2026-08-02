服务启动后，可以通过以下几种方式验证 **高并发 SSE 流式传输** 和 **客户端断开连接（Cancel/Disconnect）拦截** 功能是否正常工作。

---

## 一、 快速验证接口健康（Health Check）

在终端中执行简单的 GET 请求，确认服务和路由正常：

```bash
curl -i http://localhost:8000/health

```

**预期返回**：

```http
HTTP/1.1 200 OK
content-type: application/json
X-Trace-ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

{"status":"ok","version":"1.0.0"}

```

---

## 二、 核心功能测试

### 1. 测试 SSE 流式响应 (Stream Test)

使用带有 `-N`（无缓冲区，实时输出）参数的 `curl` 发起长文本生成请求：

```bash
curl -N -i -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3.5-35B-A3B",
    "messages": [{"role": "user", "content": "请写一篇关于人工智能发展史的千字文章。"}],
    "stream": true
  }'

```

**观察点**：

* **Header**：响应头中应包含 `Content-Type: text/event-stream` 以及 `X-Trace-ID`。


* **实时性**：终端会实时逐字/逐 Token 打字式输出 `data: {...}`，而不是一次性返回。

---

### 2. 测试客户端断开拦截 (Disconnect & Cancel Handling)

这是 **MVP 1 最核心的省 Token 逻辑**，验证步骤如下：

1. 运行上一步的 `curl -N -X POST ...` 请求命令，让大模型开始输出大段文本。
2. 在流式输出进行到一半时，在终端直接按下 **`Ctrl + C`** 强行中断请求。
3. 查看服务端的控制台日志（Console Log）。

**预期日志输出**：
你将在服务端日志中看到类似于以下的提示，表明服务端感知到了客户端断开并立刻终止了 Upstream API 的读取循环：

```text
2026-08-02 08:30:00.123 | INFO     | [TraceID: a1b2c3d4-...] | Incoming request: POST /api/v1/chat/completions[cite: 3, 10]
2026-08-02 08:30:00.456 | INFO     | [TraceID: a1b2c3d4-...] | Upstream connection established. Starting chunk streaming...[cite: 6, 10]
2026-08-02 08:30:02.789 | WARNING  | [TraceID: a1b2c3d4-...] | Client connection disconnected! Terminating upstream stream immediately.[cite: 6, 10]
2026-08-02 08:30:02.790 | INFO     | [TraceID: a1b2c3d4-...] | SSE Stream response cycle finished.[cite: 6, 10]

```

---

### 3. 测试速率限制 (Rate Limiting Test)

项目内置了 SlowAPI 进行频控（默认配置：`60 次/分钟`）。

使用 bash 快速循环触发请求测试限流：

```bash
for i in {1..65}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/v1/chat/completions -H "Content-Type: application/json" -d '{"messages": [{"role": "user", "content": "hi"}], "stream": true}'; done

```

**观察点**：
前 60 次请求返回 `200`，第 61 次开始应返回 **`429 Too Many Requests`**。

---

### 4. 前端交互可视化测试 (浏览器 Console)

可以在浏览器的开发者工具（F12）-> **Console** 标签页中粘贴以下 JavaScript 代码直接进行实时流式渲染测试：

```javascript
async function testSSE() {
  const response = await fetch('http://localhost:8000/api/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: 'deepseek-chat',
      messages: [{ role: 'user', content: '写一首关于秋天的小诗' }],
      stream: true
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    console.log("收到 Chunk:", decoder.decode(value));
  }
}

testSSE();

```

通过以上 4 步测试，即可完成 MVP 1 所有核心技术目标的完整闭环测试！