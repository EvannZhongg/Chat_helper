import hashlib  # <-- 1. 确保导入 hashlib
from typing import List
from fastapi import APIRouter, File, UploadFile, Path, HTTPException

# 2. 导入所有需要的新模型
from app.core.models import Message, ImportResult, BatchImportResponse, VLMUsage
from app.services import vlm_service, profile_service

router = APIRouter(prefix="/import", tags=["Import (Phase 1)"])


@router.post("/{profile_id}/upload_screenshots", response_model=BatchImportResponse)
async def upload_screenshots(
        profile_id: str = Path(..., description="要导入的Profile ID"),
        files: List[UploadFile] = File(..., description="聊天记录截图")
):
    """
    上传一张或多张截图进行VLM解析。

    此API将 *依次* 解析每张图片，并返回所有结果的聚合。
    """
    try:
        profile = profile_service.get_profile(profile_id)
    except HTTPException as e:
        # 如果 profile_id 无效，提前返回
        raise e

    batch_results = []
    total_usage = VLMUsage()  # 3. 初始化总消耗

    for file in files:
        image_bytes = await file.read()
        # 修正：使用 sha256
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        if profile_service.check_if_source_processed(profile_id, image_hash):
            continue

        # 4. 正确解包 vlm_service 返回的元组 (messages, usage)
        parsed_messages, usage = await vlm_service.parse_image_to_messages(image_bytes, image_hash)

        # 5. 累加Token
        total_usage.prompt_tokens += usage.prompt_tokens
        total_usage.completion_tokens += usage.completion_tokens
        total_usage.total_tokens += usage.total_tokens

        # 6. 添加入结果列表
        batch_results.append(ImportResult(
            messages=parsed_messages,
            usage=usage,
            image_hash=image_hash
        ))

        # 7. 标记为已处理
        profile_service.add_processed_source(profile_id, image_hash)

    # 8. 返回新的 BatchImportResponse 模型
    return BatchImportResponse(results=batch_results, total_usage=total_usage)