import json
import os
# [MODIFIED] 导入 List 和 Optional
from typing import List, Optional, Tuple, Set
from app.core.config import settings
# [MODIFIED] 导入所有需要的模型，包括新的 Persona 和 Insight 模型
from app.core.models import (
    Profile, Message, Event, UpdateProfileNamesRequest,
    UserPersona, OpponentPersona, ContextualInsight
)
from fastapi import HTTPException
import glob
import datetime
from zoneinfo import ZoneInfo # [新增] 用于时区转换

# 确保数据目录存在
os.makedirs(settings.DATA_PATH, exist_ok=True)


def get_profile_path(profile_id: str) -> str:
    """获取主 Profile JSON 文件的路径"""
    return os.path.join(settings.DATA_PATH, f"profile_{profile_id}.json")


# [新增] 获取 Event JSON 文件的路径
def get_event_path(profile_id: str) -> str:
    """获取事件 JSON 文件的路径"""
    return os.path.join(settings.DATA_PATH, f"event_{profile_id}.json")


# --- [新增] Persona 路径辅助函数 ---
def get_user_persona_path(profile_id: str) -> str:
    """获取用户画像 JSON 文件的路径"""
    return os.path.join(settings.DATA_PATH, f"persona_user_{profile_id}.json")


def get_opponent_persona_path(profile_id: str) -> str:
    """获取对方画像 JSON 文件的路径"""
    return os.path.join(settings.DATA_PATH, f"persona_opponent_{profile_id}.json")


# --- [新增] Insight 路径辅助函数 ---
def get_insights_path(profile_id: str) -> str:
    """获取上下文洞察 JSON 文件的路径"""
    return os.path.join(settings.DATA_PATH, f"insights_{profile_id}.json")


# --- Event Load/Save ---

def load_events(profile_id: str) -> List[Event]:
    """从单独的文件加载事件列表"""
    filepath = get_event_path(profile_id)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            events_data = json.load(f)
            # 使用 Pydantic 解析列表中的每个事件字典
            return [Event(**event_dict) for event_dict in events_data]
    except (json.JSONDecodeError, Exception) as e:
        print(f"Warning: Could not load or parse events file {filepath}: {e}")
        return []  # 出错时返回空列表


def save_events(profile_id: str, events: List[Event]):
    """将事件列表保存到单独的文件"""
    filepath = get_event_path(profile_id)
    try:
        # 将 Event 对象列表转换为字典列表以便 JSON 序列化
        events_dict_list = [event.model_dump(mode='json') for event in events]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(events_dict_list, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"!!! ERROR SAVING EVENTS for profile {profile_id}: {e}")
        # raise HTTPException(status_code=500, detail=f"Failed to save events: {e}")


# --- Persona (User) Load/Save ---

def load_user_persona(profile_id: str) -> Optional[UserPersona]:
    """从单独的文件加载用户画像"""
    filepath = get_user_persona_path(profile_id)
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return UserPersona(**data)
    except Exception as e:
        print(f"Warning: Could not load or parse user persona {filepath}: {e}")
        return None


def save_user_persona(persona: UserPersona):
    """将用户画像保存到单独的文件"""
    filepath = get_user_persona_path(persona.profile_id)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(persona.model_dump(mode='json'), f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"!!! ERROR SAVING USER PERSONA for profile {persona.profile_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save user persona: {e}")


# --- Persona (Opponent) Load/Save ---

def load_opponent_persona(profile_id: str) -> Optional[OpponentPersona]:
    """从单独的文件加载对方画像"""
    filepath = get_opponent_persona_path(profile_id)
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return OpponentPersona(**data)
    except Exception as e:
        print(f"Warning: Could not load or parse opponent persona {filepath}: {e}")
        return None


def save_opponent_persona(persona: OpponentPersona):
    """将对方画像保存到单独的文件"""
    filepath = get_opponent_persona_path(persona.profile_id)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(persona.model_dump(mode='json'), f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"!!! ERROR SAVING OPPONENT PERSONA for profile {persona.profile_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save opponent persona: {e}")


# --- [新增] Contextual Insight Load/Save ---

def get_insights_path(profile_id: str) -> str:
    """获取上下文洞察 JSON 文件的路径"""
    return os.path.join(settings.DATA_PATH, f"insights_{profile_id}.json")

def load_insights(profile_id: str) -> List[ContextualInsight]:
    """
    [修改后] 从单独的文件加载上下文洞察列表。
    兼容旧数据（可能没有 importance_score 字段）。
    """
    filepath = get_insights_path(profile_id)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
            insights = []
            for data in data_list:
                # 手动处理日期和 Set 的转换 (保持不变)
                data['analysis_date'] = datetime.date.fromisoformat(data['analysis_date'])
                data['processed_item_ids'] = set(data.get('processed_item_ids', []))

                # [!! 新增 !!] 为旧数据提供 importance_score 默认值
                # 如果 JSON 中没有 'importance_score' 键，Pydantic 会使用模型定义的默认值 (0)
                # 但为了更明确，我们也可以在这里显式处理 .get()
                # data['importance_score'] = data.get('importance_score', 0) # 这行其实 Pydantic 会自动做

                # 使用 Pydantic 解析，它会自动处理缺失字段的默认值
                try:
                    insights.append(ContextualInsight(**data))
                except Exception as pydantic_error: # 捕获可能的 Pydantic 解析错误
                    print(f"Warning: Could not parse insight data: {data}. Error: {pydantic_error}")
                    continue # 跳过无法解析的数据

            return insights
    except Exception as e:
        print(f"Warning: Could not load or parse insights {filepath}: {e}")
        return []

def save_insights(profile_id: str, insights: List[ContextualInsight]):
    """将上下文洞察列表保存到单独的文件。(通常无需修改)"""
    filepath = get_insights_path(profile_id)
    try:
        def json_serializer(obj):
            if isinstance(obj, datetime.date): return obj.isoformat()
            if isinstance(obj, set): return list(obj)
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(
                # model_dump 会自动包含 importance_score
                [item.model_dump(mode='json') for item in insights],
                f, indent=4, ensure_ascii=False, default=json_serializer
            )
    except Exception as e:
        print(f"!!! ERROR SAVING INSIGHTS for profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save insights")

def get_profile_date_range(profile_id: str) -> Optional[Tuple[datetime.date, datetime.date]]:
    """计算 Profile 中所有消息和事件的最早和最晚日期"""
    try:
        profile = get_profile(profile_id) # 加载 Profile (包含 messages 和 events)
    except HTTPException:
        return None

    all_timestamps = [m.timestamp for m in profile.messages] + [e.timestamp for e in profile.events]

    if not all_timestamps:
        return None

    # 确保所有时间戳都是 aware 的 (转换为 UTC)
    aware_timestamps = [_normalize_to_utc(ts) for ts in all_timestamps]

    min_ts = min(aware_timestamps)
    max_ts = max(aware_timestamps)

    # 转换为本地日期 (假设服务器/用户在东八区)
    # 注意：这里我们只关心日期，时区影响较小，但最好明确
    local_tz = ZoneInfo("Asia/Shanghai") # 或者 "Etc/GMT-8"
    min_date_local = min_ts.astimezone(local_tz).date()
    max_date_local = max_ts.astimezone(local_tz).date()

    return min_date_local, max_date_local

# --- Core Profile Functions ---
def check_if_date_analyzed(profile_id: str, analysis_date: datetime.date) -> bool:
    """检查指定日期是否已存在对应的 Insight"""
    insights = load_insights(profile_id)
    return any(insight.analysis_date == analysis_date for insight in insights)

def get_profile(profile_id: str) -> Profile:
    """
    获取 Profile 数据，并合并从单独文件加载的事件列表。
    (注意: 此函数不加载 Persona 或 Insights，它们是独立获取的)
    """
    filepath = get_profile_path(profile_id)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # 1. 加载主 Profile 数据
            profile_data = json.load(f)
            # 2. [重要] 创建 Profile 对象时，忽略文件中的 'events' 字段
            profile = Profile(**{k: v for k, v in profile_data.items() if k != 'events'})

            # 3. 从单独的文件加载事件
            loaded_events = load_events(profile_id)

            # 4. 将加载的事件附加到 Profile 对象上
            profile.events = loaded_events

            return profile

    except Exception as e:
        print(f"Error loading profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load profile data: {e}")


def save_profile(profile: Profile):
    """
    保存主 Profile 数据，[重要] 排除 events 字段。
    (注意: 此函数不保存 Persona 或 Insights)
    """
    filepath = get_profile_path(profile.profile_id)
    try:
        # 1. [重要] 序列化时排除 events 字段
        profile_dict = profile.model_dump(mode='json', exclude={'events'})

        # 2. 写入主 Profile 文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile_dict, f, indent=4, ensure_ascii=False)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {e}")


def _normalize_to_utc(ts: datetime.datetime) -> datetime.datetime:
    """(此函数保持不变)"""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=datetime.timezone.utc)
    return ts.astimezone(datetime.timezone.utc)


# --- Data Update Functions ---

def add_event_to_profile(profile_id: str, event: Event) -> Profile:
    """
    添加一个新事件到单独的事件文件，并按时间排序后保存。
    最后返回完整的 Profile 对象 (包含更新后的事件列表)。
    """
    current_events = load_events(profile_id)
    current_events.append(event)
    current_events.sort(key=lambda e: _normalize_to_utc(e.timestamp))
    save_events(profile_id, current_events)

    # 重新加载完整的 Profile (现在会包含新保存的事件) 并返回
    return get_profile(profile_id)


def add_messages_to_profile(profile_id: str, messages: List[Message]) -> Profile:
    """(此函数保持不变，它只操作主 profile 文件)"""
    profile = get_profile(profile_id)
    profile.messages.extend(messages)
    profile.messages.sort(key=lambda m: _normalize_to_utc(m.timestamp))
    new_hashes_to_process = set()
    for msg in messages:
        if msg.source_image_hash and msg.source_image_hash != 'manual_entry':
            new_hashes_to_process.add(msg.source_image_hash)
    for hash_val in new_hashes_to_process:
        if hash_val not in profile.processed_sources:
            profile.processed_sources.append(hash_val)

    save_profile(profile)
    return get_profile(profile_id)


def add_processed_source(profile_id: str, image_hash: str):
    """(此函数保持不变)"""
    profile = get_profile(profile_id)
    if image_hash not in profile.processed_sources:
        profile.processed_sources.append(image_hash)
        save_profile(profile)


def check_if_source_processed(profile_id: str, image_hash: str) -> bool:
    """(此函数保持不变)"""
    try:
        profile = get_profile(profile_id)
        return image_hash in profile.processed_sources
    except HTTPException as e:
        if e.status_code == 404:
            return False
        raise e


def list_all_profiles() -> List[Profile]:
    """(此函数逻辑不变，get_profile 会自动合并事件)"""
    profiles = []
    search_path = os.path.join(settings.DATA_PATH, "profile_*.json")
    for filepath in glob.glob(search_path):
        try:
            profile_id = os.path.basename(filepath).replace("profile_", "").replace(".json", "")
            profiles.append(get_profile(profile_id))
        except Exception as e:
            print(f"Warning: Skipping profile file {filepath} due to error: {e}")
            continue
    profiles.sort(key=lambda p: p.created_at, reverse=True)
    return profiles


def update_profile(profile_id: str, updates: UpdateProfileNamesRequest) -> Profile:
    """(此函数保持不变)"""
    profile = get_profile(profile_id)
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    updated_profile = profile.model_copy(update=update_data)
    save_profile(updated_profile)
    return get_profile(profile_id)