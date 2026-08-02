from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = Field(default="Qwen/Qwen3.5-35B-A3B", description="Model name")
    messages: List[Message]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = Field(default=True, description="Must be true for SSE")
