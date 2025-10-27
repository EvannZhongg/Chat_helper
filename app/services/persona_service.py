# app/services/persona_service.py

import json
import datetime
from typing import Dict, Any, List, Set, Tuple, Union  # [!!] 修复：导入 Union
from zoneinfo import ZoneInfo
from fastapi import HTTPException

# 导入 settings
from app.core.config import settings
# 导入所有需要的模型
from app.core.models import (
    UserPersona, OpponentPersona, ContextualInsight, Message, Event, Profile
)
from app.services import profile_service
from app.services.llm_client import llm_client
# 导入所有需要的 Prompts
from app.core.prompts import (
    PERSONA_USER_SUMMARIZE_PROMPT,
    PERSONA_OPPONENT_BASIC_EXTRACT_PROMPT,
    PERSONA_EXTRACT_AND_SUMMARIZE_PROMPT,
    PROMPT_PERSONA_USER,
    PROMPT_PERSONA_OPPONENT,
    PERSONA_CHAT_ANALYSIS_UPDATE_PROMPT  # [!!] 导入新 Prompt
)

# 本地时区定义 (保持不变)
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def _format_data_for_llm(
    messages: List[Message],
    events: List[Event],
    user_name: str,
    opponent_name: str,
    target_date_local: datetime.date
) -> Tuple[str, Set[str], int, int]: # [!!] 修改返回值类型
    """
    [修改后] 将消息和事件列表格式化为 LLM 可读的纯文本日志，
    并返回来源 ID Set、当天的消息数、当天的事件数。
    仅包含目标日期当天的数据。
    """
    combined_list: List[Union[Message, Event]] = messages + events

    log_entries = []
    processed_ids = set()
    message_count = 0 # [!!] 新增
    event_count = 0   # [!!] 新增

    for item in combined_list:
        item_date_local = item.timestamp.astimezone(LOCAL_TZ).date()
        if item_date_local != target_date_local:
            continue

        local_time_str = item.timestamp.astimezone(LOCAL_TZ).strftime('%H:%M')
        item_id = ""
        entry = ""
        is_message = False # [!!] 标记类型

        if isinstance(item, Message):
            item_id = item.message_id
            sender_name = "System"
            if item.sender == "User 1": sender_name = user_name
            elif item.sender == "User 2": sender_name = opponent_name
            entry = f"[{local_time_str}] {sender_name}: {item.text or ''} (Type: {item.content_type})"
            is_message = True # [!!] 标记为消息
        elif isinstance(item, Event):
            item_id = item.event_id
            entry = f"[{local_time_str}] [!! 离线事件 !!]: {item.summary}"
            # is_message 保持 False

        if entry and item_id:
            log_entries.append(entry)
            processed_ids.add(item_id)
            # [!!] 根据类型计数
            if is_message:
                message_count += 1
            else:
                event_count += 1

    return "\n".join(log_entries), processed_ids, message_count, event_count # [!!] 返回计数值


def _merge_opponent_info(
        existing_info: Dict[str, str],
        new_info: Dict[str, str]
) -> Dict[str, str]:
    """
    [新增] 实现 "A:1" + "A:2" = "A: 1 & 2" 逻辑 (保持不变)
    """
    # ... (代码保持不变) ...
    merged = existing_info.copy()
    for key, new_value in new_info.items():
        if key in merged and merged[key] != new_value:
            if new_value not in merged[key]:
                merged[key] = f"{merged[key]} & {new_value}"
        else:
            merged[key] = new_value
    return merged


# --- 手动更新函数 (保持不变) ---
async def generate_user_persona_summary(profile_id: str, description: str) -> UserPersona:
    """ (代码保持不变) """
    # ... (代码保持不变) ...
    try:
        prompt = PERSONA_USER_SUMMARIZE_PROMPT.format(description=description)
        completion = await llm_client.chat.completions.create(
            model=settings.LLM_MODEL_NAME, messages=[{"role": "user", "content": prompt}], temperature=0.3)
        summary = completion.choices[0].message.content.strip()
        persona = profile_service.load_user_persona(profile_id)
        if not persona: persona = UserPersona(profile_id=profile_id)
        persona.self_summary = summary
        persona.last_updated = datetime.datetime.now(datetime.timezone.utc)
        profile_service.save_user_persona(persona)
        return persona
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")


async def extract_opponent_basic_info(profile_id: str, description: str) -> OpponentPersona:
    """ (代码保持不变) """
    # ... (代码保持不变) ...
    try:
        prompt = PERSONA_OPPONENT_BASIC_EXTRACT_PROMPT.format(description=description)
        completion = await llm_client.chat.completions.create(
            model=settings.LLM_MODEL_NAME, messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, temperature=0.0)
        extracted_data = json.loads(completion.choices[0].message.content)
        persona = profile_service.load_opponent_persona(profile_id)
        if not persona: persona = OpponentPersona(profile_id=profile_id)
        persona.basic_info.update(extracted_data)
        persona.last_updated = datetime.datetime.now(datetime.timezone.utc)
        profile_service.save_opponent_persona(persona)
        return persona
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")


# --- [!!! 修改核心自动分析逻辑 !!!] ---
async def analyze_profile_incrementally(profile_id: str) -> Dict[str, Any]:
    """
    [Phase 2 - 核心自动分析 - 已修改]
    按天进行:
    1. 提取当天信息更新 Opponent basic_info。
    2. 生成当天 ContextualInsight 摘要，并计算重要性评分。
    3. 基于前一天 chat_analysis 和当天日志，更新 Opponent chat_analysis。
    """
    # ... (1. 获取日期范围 - 不变) ...
    # ... (2. 加载 Profile 数据 - 不变) ...
    # ... (3. 加载现有 Insights - 不变) ...
    # ... (4. 加载 Opponent Persona - 不变) ...
    date_range = profile_service.get_profile_date_range(profile_id)
    if not date_range: raise HTTPException(status_code=400, detail="无法确定日期范围，可能没有数据。")
    min_date, max_date = date_range
    try: profile = profile_service.get_profile(profile_id)
    except HTTPException as e: raise e
    existing_insights = profile_service.load_insights(profile_id)
    analyzed_dates = {insight.analysis_date for insight in existing_insights}
    opponent_persona = profile_service.load_opponent_persona(profile_id)
    if not opponent_persona: opponent_persona = OpponentPersona(profile_id=profile_id)

    # 5. 迭代处理每一天 (循环主体修改)
    current_date = min_date
    total_days = (max_date - min_date).days + 1
    processed_count = 0
    skipped_count = 0
    new_insights_list = []

    while current_date <= max_date:
        print(f"--- Analyzing date: {current_date.isoformat()} for profile {profile_id} ---")

        # 检查是否已分析 (不变)
        if current_date in analyzed_dates:
            print(f"Skipping {current_date.isoformat()} - already analyzed.")
            skipped_count += 1
            current_date += datetime.timedelta(days=1)
            continue

        # [!!] 修改: 获取消息数和事件数
        # 格式化当天数据 (现在返回4个值)
        chat_log, processed_ids, day_message_count, day_event_count = _format_data_for_llm(
            profile.messages, profile.events, profile.user_name, profile.opponent_name, current_date
        )

        # 如果当天没有数据，则跳过 (不变)
        if not chat_log:
            print(f"Skipping {current_date.isoformat()} - no data found for this day.")
            skipped_count += 1
            current_date += datetime.timedelta(days=1)
            continue

        # --- LLM 调用 1: 提取 basic_info + 生成 Insight summary (不变) ---
        try:
            prompt1 = PERSONA_EXTRACT_AND_SUMMARIZE_PROMPT.format(
                user_name=profile.user_name, opponent_name=profile.opponent_name, chat_log=chat_log)
            completion1 = await llm_client.chat.completions.create(
                model=settings.LLM_MODEL_NAME, messages=[{"role": "user", "content": prompt1}],
                response_format={"type": "json_object"}, temperature=0.2)
            response_data1 = json.loads(completion1.choices[0].message.content)
            extracted_info = response_data1.get("extracted_info", {})
            insight_summary = response_data1.get("summary", "总结失败")
            print(f"LLM Call 1 (Info/Summary) successful for {current_date.isoformat()}.")
        except Exception as e:
            print(f"!!! LLM Call 1 (Info/Summary) failed for date {current_date.isoformat()}: {e}")
            skipped_count += 1; current_date += datetime.timedelta(days=1); continue

        # 更新 Opponent Persona 的 basic_info (不变)
        opponent_persona.basic_info = _merge_opponent_info(opponent_persona.basic_info, extracted_info)

        # --- LLM 调用 2: 更新 chat_analysis (不变) ---
        previous_analysis = opponent_persona.chat_analysis or "这是第一次分析，请根据今天的日志进行总结。"
        try:
            prompt2 = PERSONA_CHAT_ANALYSIS_UPDATE_PROMPT.format(previous_analysis=previous_analysis, daily_log=chat_log)
            completion2 = await llm_client.chat.completions.create(
                model=settings.LLM_MODEL_NAME, messages=[{"role": "user", "content": prompt2}], temperature=0.4)
            updated_analysis = completion2.choices[0].message.content.strip()
            opponent_persona.chat_analysis = updated_analysis # 更新 chat_analysis
            print(f"LLM Call 2 (Chat Analysis Update) successful for {current_date.isoformat()}.")
        except Exception as e:
            print(f"!!! LLM Call 2 (Chat Analysis Update) failed for date {current_date.isoformat()}: {e}")
            # 失败不中断，chat_analysis 保持不变

        # --- [!! 新增 !!] 计算重要性评分 ---
        importance_score = (day_message_count * 1) + (day_event_count * 10)
        print(f"Calculated importance score for {current_date.isoformat()}: {importance_score} ({day_message_count} msgs, {day_event_count} events)")

        # --- 处理 Insight (修改：加入评分) ---
        new_insight = ContextualInsight(
            profile_id=profile_id,
            analysis_date=current_date,
            summary=insight_summary,
            processed_item_ids=processed_ids,
            importance_score=importance_score # [!!] 传入计算好的分数
        )
        existing_insights.append(new_insight)
        new_insights_list.append(new_insight)
        processed_count += 1

        # 移动到下一天 (不变)
        current_date += datetime.timedelta(days=1)

    # 6. 循环结束后，统一保存更新 (不变)
    try:
        opponent_persona.last_updated = datetime.datetime.now(datetime.timezone.utc)
        profile_service.save_opponent_persona(opponent_persona)
        existing_insights.sort(key=lambda x: x.analysis_date, reverse=True)
        profile_service.save_insights(profile_id, existing_insights)
        print(f"--- Analysis complete for profile {profile_id}. Saved persona and insights. ---")
    except Exception as e:
        print(f"!!! Error saving analysis results for profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="保存分析结果时出错")

    # 7. 返回处理结果统计 (不变)
    return {
        "message": f"分析完成。总共处理天数: {total_days}, 新增洞察: {processed_count}, 跳过天数: {skipped_count}.",
        "total_days": total_days,
        "processed_count": processed_count,
        "skipped_count": skipped_count,
        "new_insights": [ins.model_dump(mode='json') for ins in new_insights_list] # Pydantic v2 默认会包含所有字段
    }