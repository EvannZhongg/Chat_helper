# app/services/assist_tools.py

import datetime
import json
from typing import List, Dict, Union
from zoneinfo import ZoneInfo # [!!] 确保导入 ZoneInfo

from app.services import profile_service
from app.core.models import Message, Event, OpponentPersona, ContextualInsight

# [!!] 复用 persona_service 中的本地时区定义
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

#
# 注意：所有工具的最终返回都应该是序列化后的字符串 (如 JSON)，以便 LLM 读取。
#

def get_opponent_persona_details(profile_id: str) -> str:
    """
    获取对方画像(OpponentPersona)的完整详细信息，包括所有 basic_info 和 chat_analysis。(保持不变)
    """
    try:
        persona = profile_service.load_opponent_persona(profile_id)
        if not persona:
            return json.dumps({"error": "Opponent persona not found."})
        # 只返回对 Agent 有用的
        return persona.model_dump_json(include={'basic_info', 'chat_analysis', 'last_updated'})
    except Exception as e:
        return json.dumps({"error": f"Failed to load opponent persona: {e}"})

# --- [!!! 修改此函数 !!!] ---
def get_recent_chat_history(profile_id: str, dates: List[str]) -> str:
    """
    [修改后] 获取指定日期列表的 *详细* 聊天记录 (Messages)。
    Agent 可以提供一个或多个 'YYYY-MM-DD' 格式的日期字符串。
    """
    if not dates:
        return json.dumps({"error": "No dates provided for chat history retrieval."})

    try:
        # 1. 将输入的日期字符串转换为 date 对象集合，便于查找
        target_dates = set()
        for date_str in dates:
            try:
                target_dates.add(datetime.date.fromisoformat(date_str))
            except (ValueError, TypeError):
                # 忽略无效的日期格式
                print(f"Warning: Invalid date format '{date_str}' provided to get_recent_chat_history. Skipping.")
                pass

        if not target_dates:
             return json.dumps({"error": "No valid dates provided after parsing."})

        # 2. 加载 Profile 数据
        profile = profile_service.get_profile(profile_id)

        # 3. 筛选指定日期的消息
        selected_messages = []
        for msg in profile.messages:
            # 将消息时间戳转换为本地日期
            msg_local_date = msg.timestamp.astimezone(LOCAL_TZ).date()
            # 检查本地日期是否存在于目标日期集合中
            if msg_local_date in target_dates:
                selected_messages.append(msg)

        # 4. 按时间戳排序筛选出的消息
        selected_messages.sort(key=lambda m: profile_service._normalize_to_utc(m.timestamp))

        # 5. 返回 JSON 字符串
        return json.dumps([m.model_dump(mode='json') for m in selected_messages])

    except Exception as e:
        return json.dumps({"error": f"Failed to load messages for specified dates: {e}"})
# --- [!!! 修改结束 !!!] ---


def get_recent_events(profile_id: str, days: int = 7) -> str:
    """
    获取最近 N 天的 *详细* 离线事件 (Events)。(保持不变)
    """
    try:
        events = profile_service.load_events(profile_id)
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        recent_events = [
            e for e in events
            if profile_service._normalize_to_utc(e.timestamp) >= cutoff_date
        ]
        recent_events.sort(key=lambda e: e.timestamp)
        return json.dumps([e.model_dump(mode='json') for e in recent_events])
    except Exception as e:
        return json.dumps({"error": f"Failed to load events: {e}"})


def search_insights_by_keyword(profile_id: str, keyword: str) -> str:
    """
    根据关键词搜索 *所有* 历史洞察 (Insights) 的摘要。(保持不变)
    """
    try:
        insights = profile_service.load_insights(profile_id)
        found_insights = [
            i for i in insights
            if keyword.lower() in i.summary.lower()
        ]
        found_insights.sort(key=lambda i: i.analysis_date, reverse=True)
        return json.dumps([i.model_dump(mode='json') for i in found_insights])
    except Exception as e:
        return json.dumps({"error": f"Failed to search insights: {e}"})

# 映射工具名称到函数 (保持不变)
available_tools = {
    "get_opponent_persona_details": get_opponent_persona_details,
    "get_recent_chat_history": get_recent_chat_history, # 名称不变，但函数实现已更新
    "get_recent_events": get_recent_events,
    "search_insights_by_keyword": search_insights_by_keyword,
}