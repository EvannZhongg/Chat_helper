from openai import AsyncOpenAI
from app.core.config import settings

# VLM 客户端 (用于解析截图)
# 使用 VLM_API_KEY 和 VLM_API_BASE
vlm_client = AsyncOpenAI(
    api_key=settings.VLM_API_KEY,
    base_url=settings.VLM_API_BASE,
)

# LLM 客户端 (未来用于对话辅助)
# 使用 LLM_API_KEY 和 LLM_API_BASE
llm_client = AsyncOpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_API_BASE,
)