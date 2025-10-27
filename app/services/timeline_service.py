import datetime
from collections import defaultdict
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Union, Literal, Optional  # [!! 修复 !!] 导入 Literal 和 Optional
from pydantic import BaseModel  # [!! 修复 !!] 导入 BaseModel

from app.services import profile_service
from app.core.models import Message, Event, ContextualInsight, Profile

# 确定用于“分天”的本地时区
# 我们复用 persona_service 中使用的时区
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


# 定义返回给前端的单个“时间项”的模型
class TimelineItem(BaseModel):
    item_type: Literal["message", "event"]
    timestamp: datetime.datetime
    data: Dict[str, Any]  # 存储 Message 或 Event 的核心数据


# 定义返回给前端的“日期大节点”的模型
class DateNode(BaseModel):
    date: datetime.date
    item_count: int
    insight_summary: Optional[str] = None  # 当天的洞察总结
    items: List[TimelineItem]  # 包含当天所有聊天和事件


def get_timeline_data_for_profile(profile_id: str) -> List[DateNode]:
    """
    聚合 Profile 的所有 messages, events, 和 insights，
    并按日期分组返回。
    """

    # 1. 一次性加载所有数据
    try:
        # get_profile 已经智能地合并了 messages 和 events
        profile = profile_service.get_profile(profile_id)
        insights = profile_service.load_insights(profile_id)
    except Exception as e:
        # 如果 Profile 加载失败，则返回空
        print(f"Error loading data for timeline: {e}")
        return []

    # 2. 创建一个 Insight 摘要的快速查找字典
    # (key 是 date 对象)
    insight_map: Dict[datetime.date, str] = {
        insight.analysis_date: insight.summary for insight in insights
    }

    # 3. 将 Messages 和 Events 合并到一个统一的列表中
    all_items: List[TimelineItem] = []

    for msg in profile.messages:
        all_items.append(TimelineItem(
            item_type="message",
            timestamp=msg.timestamp,
            # 排除 'timestamp'，因为它已经在 TimelineItem 的顶层
            data=msg.model_dump(mode='json', exclude={'timestamp'})
        ))

    for evt in profile.events:
        all_items.append(TimelineItem(
            item_type="event",
            timestamp=evt.timestamp,
            data=evt.model_dump(mode='json', exclude={'timestamp'})
        ))

    # 4. 按时间戳对所有项目进行排序 (确保 UTC 比较)
    all_items.sort(key=lambda x: profile_service._normalize_to_utc(x.timestamp))

    # 5. 按“本地日期”对项目进行分组
    #    (使用 defaultdict 可以让 .append() 更简单)
    grouped_by_date = defaultdict(list)

    for item in all_items:
        # 关键：将 UTC 时间戳转换为本地日期
        local_date = item.timestamp.astimezone(LOCAL_TZ).date()
        grouped_by_date[local_date].append(item)

    # 6. 构建最终的 DateNode 列表
    date_nodes: List[DateNode] = []

    # 我们希望最新的日期在最前面
    sorted_dates = sorted(grouped_by_date.keys(), reverse=True)

    for date_obj in sorted_dates:
        items_for_day = grouped_by_date[date_obj]

        node = DateNode(
            date=date_obj,
            item_count=len(items_for_day),
            # 从 map 中获取当天的 Insight 总结
            insight_summary=insight_map.get(date_obj, None),
            items=items_for_day
        )
        date_nodes.append(node)

    return date_nodes