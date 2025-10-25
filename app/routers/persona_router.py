import json  # [新增] 用于处理 new_insights 转换
from fastapi import APIRouter, Path, Body, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict  # [修改] 导入 List, Dict
import datetime

# [修改] 导入 ContextualInsight
from app.core.models import UserPersona, OpponentPersona, ContextualInsight
from app.services import persona_service, profile_service

router = APIRouter(prefix="/persona", tags=["Persona (Phase 2)"])


# --- Pydantic 请求/响应体 ---

class UpdateUserPersonaRequest(BaseModel):
    description: str = Body(..., description="用户对自己的描述 (MBTI, 性格等)")


class UpdateOpponentPersonaRequest(BaseModel):
    description: str = Body(..., description="用户对对方的描述 (联系方式, 地址等)")


# [新增] 用于 GET /date_range 的响应模型
class DateRangeResponse(BaseModel):
    min_date: Optional[str] = None  # YYYY-MM-DD
    max_date: Optional[str] = None  # YYYY-MM-DD


# [新增] 用于 POST /analyze_all 的响应模型
class AnalysisResultResponse(BaseModel):
    message: str
    total_days: int
    processed_count: int
    skipped_count: int
    new_insights: List[Dict]  # 返回 JSON 兼容的 Insight 数据


# --- API 端点 ---

# --- User Persona ---
@router.get("/{profile_id}/user", response_model=UserPersona)
def get_user_persona(profile_id: str = Path(...)):
    """
    获取指定 Profile 的“用户画像”
    """
    persona = profile_service.load_user_persona(profile_id)
    if not persona:
        raise HTTPException(status_code=404, detail="User persona not found. Please create one.")
    return persona


@router.post("/{profile_id}/user", response_model=UserPersona)
async def update_user_persona_summary(
        profile_id: str = Path(...),
        request: UpdateUserPersonaRequest = Body(...)
):
    """
    根据用户输入，更新“用户画像”的自我总结
    """
    return await persona_service.generate_user_persona_summary(profile_id, request.description)


# --- Opponent Persona ---
@router.get("/{profile_id}/opponent", response_model=OpponentPersona)
def get_opponent_persona(profile_id: str = Path(...)):
    """
    获取指定 Profile 的“对方画像”
    """
    persona = profile_service.load_opponent_persona(profile_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Opponent persona not found. Please create one.")
    return persona


@router.post("/{profile_id}/opponent", response_model=OpponentPersona)
async def update_opponent_persona_info(
        profile_id: str = Path(...),
        request: UpdateOpponentPersonaRequest = Body(...)
):
    """
    根据用户输入，提取并更新“对方画像”的基础信息
    """
    return await persona_service.extract_opponent_basic_info(profile_id, request.description)


# --- Date Range & Insights ---
@router.get("/{profile_id}/date_range", response_model=DateRangeResponse)
def get_date_range(profile_id: str = Path(...)):
    """
    [新增] 获取 Profile 中数据的最早和最晚日期
    """
    date_range = profile_service.get_profile_date_range(profile_id)
    if not date_range:
        return DateRangeResponse()  # 返回空
    min_d, max_d = date_range
    return DateRangeResponse(min_date=min_d.isoformat(), max_date=max_d.isoformat())


@router.get("/{profile_id}/insights", response_model=List[ContextualInsight])
def get_all_insights(profile_id: str = Path(...)):
    """
    获取指定 Profile 的所有“上下文洞察”列表
    """
    insights = profile_service.load_insights(profile_id)
    # [修改] 不再抛出404，让前端处理空列表
    # if not insights:
    #     raise HTTPException(status_code=404, detail="No insights found for this profile.")
    return insights


# --- Analysis Trigger ---
@router.post("/{profile_id}/analyze_all", response_model=AnalysisResultResponse)
async def trigger_incremental_analysis(profile_id: str = Path(...)):
    """
    [Phase 2 按钮 - 修改后]
    触发一次增量分析，处理该 Profile 下所有未被分析过的日期。
    这是一个潜在的耗时操作。
    """
    try:
        result = await persona_service.analyze_profile_incrementally(profile_id)

        # [修改] 确保 new_insights 已经是 JSON 兼容的字典列表
        # persona_service 现在应该返回处理好的列表
        # result['new_insights'] = [
        #     json.loads(ContextualInsight(**ins_dict).model_dump_json(exclude={'processed_item_ids'})) # 可以在这里排除 ids
        #     for ins_dict in result['new_insights'] # 假设 service 返回的是 dict 列表
        # ]

        return AnalysisResultResponse(**result)

    except HTTPException as e:
        # 透传 persona_service 或 profile_service 抛出的 HTTP 异常
        raise e
    except Exception as e:
        # 捕获其他意外错误
        print(f"!!! Unexpected error during incremental analysis trigger for {profile_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"分析过程中发生意外错误: {e}")