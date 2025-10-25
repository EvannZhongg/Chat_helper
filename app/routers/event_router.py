import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Path, Body
from pydantic import BaseModel, Field
import datetime
import traceback

from app.core.models import Event, Profile
from app.services import event_service, profile_service

router = APIRouter(prefix="/events", tags=["Events (Phase 1.5)"])


# --- API 1: 分析事件 ---
class AnalyzeEventResponse(BaseModel):
    summary: str
    original_image_hash: Optional[str] = None


@router.post("/{profile_id}/analyze", response_model=AnalyzeEventResponse)
async def analyze_event(
        profile_id: str = Path(...),
        description: Optional[str] = Form(None),
        file: Optional[UploadFile] = File(None)
):
    """
    接收文本和/或图片，调用 VLM/LLM 进行分析，并返回摘要。
    会传递 user_name 和 opponent_name 给模型。
    """
    try:
        profile = profile_service.get_profile(profile_id)
    except HTTPException as e:
        raise e

    user_name = profile.user_name
    opponent_name = profile.opponent_name

    image_bytes: Optional[bytes] = None
    image_hash: Optional[str] = None
    if file:
        image_bytes = await file.read()
        image_hash = hashlib.sha256(image_bytes).hexdigest()

    summary = await event_service.analyze_event_inputs(
        description=description,
        image_bytes=image_bytes,
        user_name=user_name,
        opponent_name=opponent_name
    )

    # 保留分析结果的打印，方便调试
    print("\n" + "=" * 50)
    print(f"[Event Router] Analysis Result for profile {profile_id}:")
    print(f"Summary: {summary}")
    print("=" * 50 + "\n")

    return AnalyzeEventResponse(summary=summary, original_image_hash=image_hash)


# --- API 2: 保存事件 ---

class SaveEventRequest(BaseModel):
    summary: str
    timestamp: datetime.datetime
    original_text: Optional[str] = None
    original_image_hash: Optional[str] = None


# [恢复] 最终的 save_event 函数
@router.post("/{profile_id}/save", response_model=Profile)
def save_event(
        profile_id: str = Path(...),
        request: SaveEventRequest = Body(...)
):
    """
    将用户确认的事件摘要和时间戳保存到 Profile。
    """
    try:
        new_event = Event(
            timestamp=request.timestamp,
            summary=request.summary,
            original_text=request.original_text,
            original_image_hash=request.original_image_hash
        )

        # (TODO: 如果有 image_hash，此时应该触发保存图片文件的逻辑)

        updated_profile = profile_service.add_event_to_profile(profile_id, new_event)
        return updated_profile

    except Exception as e:
        # 保留基本的错误日志记录
        print(f"!!! ERROR SAVING EVENT for profile {profile_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error while saving event: {e}")

# 移除调试函数
# @router.get("/save") ...
