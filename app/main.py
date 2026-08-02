import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logger import logger, trace_id_ctx
from app.api.v1.chat import router as chat_router

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up High-Performance AI SSE Backend...")
    yield
    logger.info("Shutting down AI SSE Backend...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    token = trace_id_ctx.set(trace_id)
    
    start_time = time.time()
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    
    try:
        response: Response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        response.headers["X-Trace-ID"] = trace_id
        logger.info(f"Request completed in {process_time:.2f}ms | Status: {response.status_code}")
        return response
    except Exception as exc:
        logger.error(f"Unhandled exception: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "Internal server error", "trace_id": trace_id}},
            headers={"X-Trace-ID": trace_id}
        )
    finally:
        trace_id_ctx.reset(token)

app.include_router(chat_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.VERSION}
