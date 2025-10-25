import json
import os
from typing import List
from app.core.config import settings
# [修改] 导入 Event 模型
from app.core.models import Profile, Message, Event, UpdateProfileNamesRequest 
from fastapi import HTTPException
import glob 
import datetime

# 确保数据目录存在
os.makedirs(settings.DATA_PATH, exist_ok=True)


def get_profile_path(profile_id: str) -> str:
    """获取主 Profile JSON 文件的路径"""
    return os.path.join(settings.DATA_PATH, f"profile_{profile_id}.json")

# [新增] 获取 Event JSON 文件的路径
def get_event_path(profile_id: str) -> str:
    """获取事件 JSON 文件的路径"""
    return os.path.join(settings.DATA_PATH, f"event_{profile_id}.json")

# [新增] 加载事件列表的辅助函数
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
        return [] # 出错时返回空列表

# [新增] 保存事件列表的辅助函数
def save_events(profile_id: str, events: List[Event]):
    """将事件列表保存到单独的文件"""
    filepath = get_event_path(profile_id)
    try:
        # 将 Event 对象列表转换为字典列表以便 JSON 序列化
        events_dict_list = [event.model_dump(mode='json') for event in events]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(events_dict_list, f, indent=4, ensure_ascii=False)
    except Exception as e:
        # 这里使用 HTTPException 可能不太合适，因为这不是直接的API响应
        # 改为打印错误，实际应用中应考虑更健壮的错误处理
        print(f"!!! ERROR SAVING EVENTS for profile {profile_id}: {e}")
        # raise HTTPException(status_code=500, detail=f"Failed to save events: {e}")


# [修改] get_profile 函数
def get_profile(profile_id: str) -> Profile:
    """
    获取 Profile 数据，并合并从单独文件加载的事件列表。
    """
    filepath = get_profile_path(profile_id)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # 1. 加载主 Profile 数据 (可能包含旧的 events 字段)
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


# [修改] save_profile 函数
def save_profile(profile: Profile):
    """
    保存主 Profile 数据，[重要] 排除 events 字段。
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
    # ... (此函数保持不变) ...
    if ts.tzinfo is None:
        return ts.replace(tzinfo=datetime.timezone.utc)
    return ts.astimezone(datetime.timezone.utc)


# [修改] add_event_to_profile 函数
def add_event_to_profile(profile_id: str, event: Event) -> Profile:
    """
    添加一个新事件到单独的事件文件，并按时间排序后保存。
    最后返回完整的 Profile 对象 (包含更新后的事件列表)。
    """
    # 1. 加载现有的事件
    current_events = load_events(profile_id)
    
    # 2. 添加新事件
    current_events.append(event)
    
    # 3. 按时间戳排序事件列表
    current_events.sort(key=lambda e: _normalize_to_utc(e.timestamp))
    
    # 4. 保存更新后的事件列表到单独文件
    save_events(profile_id, current_events)
    
    # 5. [重要] 重新加载完整的 Profile (现在会包含新保存的事件) 并返回
    #    这确保了 API 响应与之前的行为一致
    return get_profile(profile_id)


def add_messages_to_profile(profile_id: str, messages: List[Message]) -> Profile:
    # ... (此函数保持不变，它只操作主 profile 文件) ...
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
    # [重要] 调用修改后的 save_profile，它会自动排除 events
    save_profile(profile) 
    # get_profile 会重新加载并附加 events
    return get_profile(profile_id) 


def add_processed_source(profile_id: str, image_hash: str):
    # ... (此函数保持不变) ...
    profile = get_profile(profile_id)
    if image_hash not in profile.processed_sources:
        profile.processed_sources.append(image_hash)
        save_profile(profile) # save_profile 会排除 events


def check_if_source_processed(profile_id: str, image_hash: str) -> bool:
    # ... (此函数保持不变) ...
    try:
        profile = get_profile(profile_id)
        return image_hash in profile.processed_sources
    except HTTPException as e:
        if e.status_code == 404:
            return False
        raise e


def list_all_profiles() -> List[Profile]:
    # ... (此函数逻辑不变，但现在 get_profile 会合并事件) ...
    profiles = []
    search_path = os.path.join(settings.DATA_PATH, "profile_*.json")
    for filepath in glob.glob(search_path):
        try:
            # 提取 profile_id 从文件名
            profile_id = os.path.basename(filepath).replace("profile_", "").replace(".json", "")
            # 调用 get_profile 来加载主数据并合并事件
            profiles.append(get_profile(profile_id))
        except Exception as e:
             print(f"Warning: Skipping profile file {filepath} due to error: {e}")
             continue
    profiles.sort(key=lambda p: p.created_at, reverse=True)
    return profiles


def update_profile(profile_id: str, updates: UpdateProfileNamesRequest) -> Profile:
    # ... (此函数保持不变) ...
    profile = get_profile(profile_id)
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    updated_profile = profile.model_copy(update=update_data)
    save_profile(updated_profile) # save_profile 会排除 events
    # get_profile 会重新加载并附加 events
    return get_profile(profile_id) 

