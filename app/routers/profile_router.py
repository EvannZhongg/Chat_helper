from typing import List, Optional
from fastapi import APIRouter, Body
from pydantic import BaseModel  # <-- ADD THIS LINE
from app.core.models import Profile, Message, UpdateProfileNamesRequest
from app.services import profile_service

router = APIRouter(prefix="/profiles", tags=["Profiles"])

class CreateProfileRequest(BaseModel):
    profile_name: str # e.g., "Boss"
    opponent_name: str # e.g., "Boss"
    user_name: str = "我"

@router.post("/", response_model=Profile, status_code=201)
def create_profile(request: CreateProfileRequest):
    """
    创建一个新的聊天Profile
    """
    new_profile = Profile(
        profile_name=request.profile_name,
        opponent_name=request.opponent_name,
        user_name=request.user_name
    )
    profile_service.save_profile(new_profile)
    return new_profile

@router.get("/", response_model=List[Profile])
def get_all_profiles():
    """
    获取所有已创建的Profile列表
    """
    return profile_service.list_all_profiles()

@router.get("/{profile_id}", response_model=Profile)
def get_profile(profile_id: str):
    """
    获取指定Profile的完整数据（包括所有已保存的消息）
    """
    return profile_service.get_profile(profile_id)

@router.post("/{profile_id}/messages", response_model=Profile)
def save_edited_messages(
    profile_id: str,
    messages: List[Message] = Body(...)
):
    """
    **[阶段一关键接口]**
    保存前端编辑和确认后的消息列表。
    """
    return profile_service.add_messages_to_profile(profile_id, messages)

@router.patch("/{profile_id}", response_model=Profile)
def update_profile_details(
    profile_id: str,
    request: UpdateProfileNamesRequest
):
    """
    更新Profile的名称 (我、对方、或档案名)
    """
    return profile_service.update_profile(profile_id, request)