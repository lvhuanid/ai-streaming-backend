import sys
from contextvars import ContextVar
from loguru import logger

trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="N/A")

def trace_id_filter(record):
    record["extra"]["trace_id"] = trace_id_ctx.get()
    return True

logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | [TraceID: {extra[trace_id]}] | {message}",
    filter=trace_id_filter,
    level="INFO",
    serialize=False
)
