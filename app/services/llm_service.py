import asyncio
import json
from typing import AsyncGenerator
import httpx
from fastapi import Request
from app.core.config import settings
from app.core.logger import logger

async def stream_llm_response(
    request: Request,
    model: str,
    messages: list,
    temperature: float = 0.7
) -> AsyncGenerator[str, None]:
    # Strip trailing slash to avoid double-slash (e.g. .../v1//chat/completions)
    # which causes upstream 404 on strict routers like ModelScope.
    url = f"{settings.LLM_API_BASE.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [m.dict() if hasattr(m, "dict") else m for m in messages],
        "temperature": temperature,
        "stream": True
    }

    logger.info(f"Initiating stream request to Upstream LLM ({model})")

    # Limit client connections & setup proper timeout
    timeout = httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    logger.error(f"Upstream API Error [{response.status_code}]: {err_body.decode('utf-8', errors='ignore')}")
                    yield f"data: {json.dumps({'error': f'Upstream return status {response.status_code}'})}\n\n"
                    return

                logger.info("Upstream connection established. Starting chunk streaming...")
                
                async for line in response.aiter_lines():
                    # Check if client disconnected mid-stream
                    if await request.is_disconnected():
                        logger.warning("Client connection disconnected! Terminating upstream stream immediately.")
                        break

                    if line.startswith("data: "):
                        yield f"{line}\n\n"
                        # Yield event loop control to rapidly catch disconnect cancellation
                        await asyncio.sleep(0)
                        
        except asyncio.CancelledError:
            logger.info("Async task explicitly cancelled. Releasing connection pool resources.")
            raise
        except Exception as exc:
            logger.error(f"Stream exception encountered: {str(exc)}")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            logger.info("SSE Stream response cycle finished.")
