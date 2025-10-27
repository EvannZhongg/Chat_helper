from fastapi import APIRouter, Path, Depends, HTTPException
from typing import List
import datetime

# 导入 timeline_service 和 Pydantic 模型
from app.services import timeline_service
from app.services.timeline_service import DateNode # 导入已修正的 DateNode

# (需要从 models.py 导入 Profile 和从 profile_service 导入 get_profile)
from app.core.models import Profile
from app.services import profile_service

router = APIRouter(prefix="/timeline", tags=["Timeline (Visualization)"])

# 复用 assist_router 中的依赖注入，确保 profile_id 有效
def get_profile_dependency(profile_id: str = Path(...)) -> Profile:
    try:
        # get_profile 会在找不到时自动抛出 404
        return profile_service.get_profile(profile_id)
    except HTTPException as e:
        # 重新抛出 HTTPException (如 404 Not Found)
        raise e
    except Exception as e:
        # 捕获其他意外的加载错误
        raise HTTPException(status_code=500, detail=f"Failed to load profile: {e}")


@router.get("/{profile_id}", response_model=List[DateNode])
async def get_timeline_data(
    # FastAPI 会先运行 get_profile_dependency
    profile: Profile = Depends(get_profile_dependency)
):
    """
    [新增] 获取用于时间线可视化的聚合数据。
    数据已按日期（大节点）预先分组，
    每个日期下的项目（聊天/事件）已按时间排好序。
    """
    try:
        timeline_nodes = timeline_service.get_timeline_data_for_profile(profile.profile_id)
        return timeline_nodes
    except Exception as e:
        print(f"!!! UNEXPECTED ERROR in /timeline: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成时间线时发生意外错误: {e}")