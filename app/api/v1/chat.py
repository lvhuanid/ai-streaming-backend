from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas.chat import ChatCompletionRequest
from app.services.llm_service import stream_llm_response

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/chat/completions")
@limiter.limit("60/minute")
async def create_chat_completion(
    request: Request,
    body: ChatCompletionRequest
):
    if not body.stream:
        raise HTTPException(status_code=400, detail="Only streaming mode (stream=true) is supported on this endpoint.")
    
    gen = stream_llm_response(
        request=request,
        model=body.model,
        messages=body.messages,
        temperature=body.temperature
    )

    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
