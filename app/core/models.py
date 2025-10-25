import uuid
import datetime
from pydantic import BaseModel, Field
from typing import Literal, Optional, List


# VLM解析结果的内部结构
class VLMMessageItem(BaseModel):
    sender: Literal["User 1", "User 2"]
    date: Optional[str] = None  # VLM识别的日期 (YYYY-MM-DD)
    time: Optional[str] = None  # VLM识别的时间 (HH:MM)
    content_type: Literal["text", "image", "transfer", "emoji", "system", "unknown"]
    text: Optional[str] = None  # 文本内容
    description: Optional[str] = None  # 对非文本内容的描述


# VLM必须返回的JSON格式
class VLMResponseModel(BaseModel):
    messages: List[VLMMessageItem]


# 存储在JSON文件中的标准Message格式
class Message(BaseModel):
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex}")
    timestamp: datetime.datetime
    sender: str  # "User 1", "User 2" 或 "system" (后续会被替换为 "我", "Boss")
    content_type: Literal["text", "image", "transfer", "emoji", "system", "unknown"]
    text: Optional[str] = None
    media_description: Optional[str] = None  # VLM对图片/表情包的描述

    # --- 阶段一新增字段 ---
    source_image_hash: Optional[str] = None  # 关联到源截图
    is_editable: bool = False  # 标记此消息是否为VLM失败的模板
    raw_vlm_output: Optional[str] = None  # 存储VLM原始输出，用于调试


# Profile 档案
class Profile(BaseModel):
    profile_id: str = Field(default_factory=lambda: f"prof_{uuid.uuid4().hex}")
    profile_name: str  # e.g., "Boss"
    user_name: str = "我"
    opponent_name: str  # e.g., "Boss"
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

    processed_sources: List[str] = []  # 存储已处理图片的Hash
    messages: List[Message] = []

class VLMUsage(BaseModel):
        prompt_tokens: int = 0
        completion_tokens: int = 0
        total_tokens: int = 0

class ImportResult(BaseModel):
        messages: List[Message]
        usage: VLMUsage
        image_hash: str  # 告诉前端这张图的hash

class BatchImportResponse(BaseModel):
        results: List[ImportResult]
        total_usage: VLMUsage

class UpdateProfileNamesRequest(BaseModel):
    profile_name: Optional[str] = None
    user_name: Optional[str] = None
    opponent_name: Optional[str] = None