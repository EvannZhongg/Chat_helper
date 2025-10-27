from fastapi import APIRouter, Path, Body, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# 导入 AssistService
from app.services.assist_service import AssistService
# 导入 Profile 模型和 service 以便进行依赖注入
from app.core.models import Profile
from app.services import profile_service

router = APIRouter(prefix="/assist", tags=["Assist (Phase 3)"])


# --- Pydantic 模型 ---

class AssistRequest(BaseModel):
    opponent_message: str = Body(..., description="对方的最新消息")
    user_thoughts: str = Body(..., description="我内心的真实想法")


class AssistResponse(BaseModel):
    # 这个结构必须与 STRATEGIST_PROMPT 的 JSON 输出要求一致
    strategy_analysis: str
    reply_options: List[str]
    error: Optional[str] = None


# --- 依赖注入 (Helper) ---

def get_profile_dependency(profile_id: str = Path(...)) -> Profile:
    """
    一个 FastAPI 依赖项，用于在路由处理之前加载 Profile。
    这确保了 profile_id 是有效的，并使 profile 对象可用于路由。
    """
    try:
        # get_profile 会在找不到时自动抛出 404
        return profile_service.get_profile(profile_id)
    except HTTPException as e:
        # 重新抛出 HTTPException (如 404 Not Found)
        raise e
    except Exception as e:
        # 捕获其他意外的加载错误
        raise HTTPException(status_code=500, detail=f"Failed to load profile: {e}")


# --- API 端点 ---

@router.post("/{profile_id}", response_model=AssistResponse)
async def get_assistance(
        request: AssistRequest = Body(...),
        # **关键修复**：使用 Depends 来注入 Profile
        # FastAPI 会先运行 get_profile_dependency，
        # 如果成功，会把返回的 Profile 对象传给 profile 参数
        profile: Profile = Depends(get_profile_dependency)
):
    """
    [阶段三核心接口]
    获取“社交军师”的回复建议。
    """
    try:
        # **修复**：现在我们拥有了 profile 对象的所有信息
        # 我们可以用 3 个参数安全地初始化 AssistService
        service = AssistService(
            profile_id=profile.profile_id,
            user_name=profile.user_name,
            opponent_name=profile.opponent_name
        )

        # 调用核心逻辑
        result_dict = await service.get_assistance(
            request.opponent_message,
            request.user_thoughts
        )

        # 检查 Agent 内部是否出错
        if "error" in result_dict and result_dict["error"]:
            raise HTTPException(status_code=500, detail=result_dict["error"])

        return AssistResponse(**result_dict)

    except HTTPException as e:
        # 重新抛出已知的 HTTP 异常
        raise e
    except Exception as e:
        # 捕获任何其他意外错误
        print(f"!!! UNEXPECTED ERROR in /assist: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取辅助时发生意外错误: {e}")