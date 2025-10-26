import json
import datetime
from typing import Dict, Any, List, Set, Tuple # <-- 新增 Tuple
from zoneinfo import ZoneInfo # [新增]
from fastapi import HTTPException

# 导入 settings
from app.core.config import settings
# 导入所有需要的模型
from app.core.models import (
    UserPersona, OpponentPersona, ContextualInsight, Message, Event
)
from app.services import profile_service
from app.services.llm_client import llm_client
# 导入所有需要的 Prompts
from app.core.prompts import (
    PERSONA_USER_SUMMARIZE_PROMPT,
    PERSONA_OPPONENT_BASIC_EXTRACT_PROMPT,
    PERSONA_EXTRACT_AND_SUMMARIZE_PROMPT,
    PROMPT_PERSONA_USER,
    PROMPT_PERSONA_OPPONENT
)


def _format_data_for_llm(
    messages: List[Message],
    events: List[Event],
    user_name: str,
    opponent_name: str,
    target_date_local: datetime.date # [新增] 传入目标日期
) -> (str, Set[str]): # <-- [修改] 返回 Set[str]
    """
    [修改] 将消息和事件列表格式化为 LLM 可读的纯文本日志，并返回来源 ID Set。
    仅包含目标日期当天的数据。
    """
    combined_list = messages + events

    log_entries = []
    processed_ids = set()

    local_tz = ZoneInfo("Asia/Shanghai") # 和 date_range 使用相同的时区

    for item in combined_list:
        # 检查 item 是否属于目标日期 (在本地时区下)
        item_date_local = item.timestamp.astimezone(local_tz).date()
        if item_date_local != target_date_local:
            continue # 跳过不属于当天的数据

        # 格式化时间 (只显示 HH:MM 即可)
        local_time_str = item.timestamp.astimezone(local_tz).strftime('%H:%M')

        item_id = "" # 获取 ID
        entry = ""   # 构建日志条目

        if isinstance(item, Message):
            item_id = item.message_id
            sender_name = "System"
            if item.sender == "User 1": sender_name = user_name
            elif item.sender == "User 2": sender_name = opponent_name
            entry = f"[{local_time_str}] {sender_name}: {item.text or ''} (Type: {item.content_type})"

        elif isinstance(item, Event):
            item_id = item.event_id
            entry = f"[{local_time_str}] [!! 离线事件 !!]: {item.summary}"

        if entry and item_id: # 确保有效
            log_entries.append(entry)
            processed_ids.add(item_id)

    # 按时间排序当天的条目
    # (需要从原始 item 获取时间戳来排序，这里简化处理，假设 LLM 能处理乱序)
    # 如果需要严格排序，需要稍微复杂化的处理

    return "\n".join(log_entries), processed_ids


def _merge_opponent_info(
        existing_info: Dict[str, str],
        new_info: Dict[str, str]
) -> Dict[str, str]:
    """
    [新增] 实现 "A:1" + "A:2" = "A: 1 & 2" 逻辑
    """
    merged = existing_info.copy()
    for key, new_value in new_info.items():
        if key in merged and merged[key] != new_value:
            # 如果键已存在且值不同，则合并
            if new_value not in merged[key]:  # 避免重复合并
                merged[key] = f"{merged[key]} & {new_value}"
        else:
            # 否则，添加或覆盖
            merged[key] = new_value
    return merged


async def generate_user_persona_summary(profile_id: str, description: str) -> UserPersona:
    """
    (Phase 2 手动) 根据用户输入，调用 LLM 总结“我”的画像。
    """
    try:
        # 1. 调用 LLM
        prompt = PERSONA_USER_SUMMARIZE_PROMPT.format(description=description)
        completion = await llm_client.chat.completions.create(
            # [FIXED] 使用 settings.LLM_MODEL_NAME
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        summary = completion.choices[0].message.content.strip()

        # 2. 加载现有画像 (如果存在)，否则创建新的
        persona = profile_service.load_user_persona(profile_id)
        if not persona:
            persona = UserPersona(profile_id=profile_id)

        # 3. 更新数据
        persona.self_summary = summary
        persona.last_updated = datetime.datetime.now()

        # 4. 保存
        profile_service.save_user_persona(persona)
        return persona

    except Exception as e:
        print(f"Error generating user persona summary: {e}")
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")


async def extract_opponent_basic_info(profile_id: str, description: str) -> OpponentPersona:
    """
    (Phase 2 手动) 根据用户输入，调用 LLM 提取“对方”的基础信息键值对。
    """
    try:
        # 1. 调用 LLM (要求 JSON 输出)
        prompt = PERSONA_OPPONENT_BASIC_EXTRACT_PROMPT.format(description=description)
        completion = await llm_client.chat.completions.create(
            # [FIXED] 使用 settings.LLM_MODEL_NAME (确保此模型擅长 JSON)
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        extracted_data = json.loads(completion.choices[0].message.content)

        # 2. 加载现有画像 (如果存在)，否则创建新的
        persona = profile_service.load_opponent_persona(profile_id)
        if not persona:
            persona = OpponentPersona(profile_id=profile_id)

        # 3. [重要] 合并数据：新的替换旧的 (注意：这里使用简单 update)
        persona.basic_info.update(extracted_data)
        persona.last_updated = datetime.datetime.now()

        # 4. 保存
        profile_service.save_opponent_persona(persona)
        return persona

    except json.JSONDecodeError as e:
        print(f"Error decoding LLM JSON response: {e}")
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON")
    except Exception as e:
        print(f"Error extracting opponent basic info: {e}")
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")


async def analyze_profile_incrementally(profile_id: str) -> Dict[str, Any]:
    """
    [Phase 2 - 核心自动分析]
    自动分析 Profile 中所有未处理的日期的数据。
    按天进行，提取信息更新 Opponent 画像，并创建每日 Insight。
    """
    # 1. 获取日期范围
    date_range = profile_service.get_profile_date_range(profile_id)
    if not date_range:
        raise HTTPException(status_code=400, detail="无法确定日期范围，可能没有数据。")
    min_date, max_date = date_range

    # 2. 加载 Profile 数据 (一次性加载)
    try:
        profile = profile_service.get_profile(profile_id)
    except HTTPException as e:
        raise e

    # 3. 加载现有 Insights，并创建已分析日期的 Set
    existing_insights = profile_service.load_insights(profile_id)
    analyzed_dates = {insight.analysis_date for insight in existing_insights}

    # 4. 加载 Opponent Persona (准备更新)
    opponent_persona = profile_service.load_opponent_persona(profile_id)
    if not opponent_persona:
        opponent_persona = OpponentPersona(profile_id=profile_id)

    # 5. 迭代处理每一天
    current_date = min_date
    total_days = (max_date - min_date).days + 1
    processed_count = 0
    skipped_count = 0
    new_insights_list = [] # 存储本次运行新创建的 insights

    while current_date <= max_date:
        print(f"--- Analyzing date: {current_date.isoformat()} for profile {profile_id} ---")

        # 检查是否已分析
        if current_date in analyzed_dates:
            print(f"Skipping {current_date.isoformat()} - already analyzed.")
            skipped_count += 1
            current_date += datetime.timedelta(days=1)
            continue

        # 格式化当天数据
        chat_log, processed_ids = _format_data_for_llm(
            profile.messages,
            profile.events,
            profile.user_name,
            profile.opponent_name,
            current_date # 传入目标日期
        )

        # 如果当天没有数据，则跳过
        if not chat_log:
            print(f"Skipping {current_date.isoformat()} - no data found for this day.")
            # 注意：我们不创建空的 Insight，也不标记为已分析
            skipped_count += 1 # 算作跳过
            current_date += datetime.timedelta(days=1)
            continue

        # 调用 LLM 分析
        try:
            prompt = PERSONA_EXTRACT_AND_SUMMARIZE_PROMPT.format(
                user_name=profile.user_name,
                opponent_name=profile.opponent_name,
                chat_log=chat_log
            )
            completion = await llm_client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            response_data = json.loads(completion.choices[0].message.content)
            extracted_info = response_data.get("extracted_info", {})
            summary = response_data.get("summary", "总结失败")

            print(f"LLM analysis successful for {current_date.isoformat()}.")

        except Exception as e:
            print(f"!!! LLM call failed for date {current_date.isoformat()}: {e}")
            # 如果 LLM 失败，可以选择跳过当天或停止整个过程
            # 这里选择跳过当天，继续下一天
            skipped_count += 1
            current_date += datetime.timedelta(days=1)
            continue # 跳到下一天

        # 更新 Opponent Persona (合并 KV)
        opponent_persona.basic_info = _merge_opponent_info(
            opponent_persona.basic_info, extracted_info
        )
        # (暂时不在这里保存 persona，循环结束后统一保存一次)

        # 创建新的 Insight
        new_insight = ContextualInsight(
            profile_id=profile_id,
            analysis_date=current_date,
            summary=summary,
            processed_item_ids=processed_ids
        )
        existing_insights.append(new_insight) # 加入列表准备保存
        new_insights_list.append(new_insight) # 用于返回给前端
        processed_count += 1

        # 移动到下一天
        current_date += datetime.timedelta(days=1)

    # 6. 循环结束后，统一保存更新
    try:
        # 保存合并后的 Opponent Persona
        opponent_persona.last_updated = datetime.datetime.now()
        profile_service.save_opponent_persona(opponent_persona)

        # 保存所有 Insights (包括新旧)
        existing_insights.sort(key=lambda x: x.analysis_date, reverse=True) # 按日期排序
        profile_service.save_insights(profile_id, existing_insights)
        print(f"--- Analysis complete for profile {profile_id}. Saved persona and insights. ---")

    except Exception as e:
        # 保存失败的处理
        print(f"!!! Error saving analysis results for profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="保存分析结果时出错")

    # 7. 返回处理结果统计
    return {
        "message": f"分析完成。总共处理天数: {total_days}, 新增洞察: {processed_count}, 跳过天数: {skipped_count}.",
        "total_days": total_days,
        "processed_count": processed_count,
        "skipped_count": skipped_count,
        "new_insights": [ins.model_dump(mode='json') for ins in new_insights_list] # 返回新增的 insight
    }