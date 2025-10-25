import json
import os
from typing import List
from app.core.config import settings
# [确保 Event 被导入]
from app.core.models import Profile, Message, UpdateProfileNamesRequest, Event
from fastapi import HTTPException
import glob  # 导入 glob
import datetime  # [确保 datetime 被导入]

# 确保数据目录存在
os.makedirs(settings.DATA_PATH, exist_ok=True)


def get_profile_path(profile_id: str) -> str:
    return os.path.join(settings.DATA_PATH, f"profile_{profile_id}.json")


def get_profile(profile_id: str) -> Profile:
    filepath = get_profile_path(profile_id)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Profile not found")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 使用 Pydantic 的 model_validate 确保数据符合最新模型
            return Profile.model_validate(data)
    except Exception as e:
        print(f"Error loading or validating profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load profile: {e}")


def save_profile(profile: Profile):
    filepath = get_profile_path(profile.profile_id)
    try:
        # 使用 Pydantic 的 model_dump_json 来确保 datetime 等类型被正确序列化
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(profile.model_dump_json(indent=4))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {e}")


# --- 辅助函数：标准化时间戳 ---
def _normalize_to_utc(ts: datetime.datetime) -> datetime.datetime:
    """
    标准化datetime对象：
    1. 如果是 Naive，假定它是UTC。
    2. 如果是 Aware，将其转换为UTC。
    """
    if not isinstance(ts, datetime.datetime):
        # 处理可能的 None 或无效类型
        print(f"Warning: _normalize_to_utc received non-datetime value: {ts}. Using epoch.")
        return datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

    if ts.tzinfo is None:
        # 假设 Naive (朴素) 时间本来就是 UTC
        return ts.replace(tzinfo=datetime.timezone.utc)
    # 将 Aware (带时区) 时间统一转换为 UTC
    return ts.astimezone(datetime.timezone.utc)


# --- 消息相关函数 ---
def add_messages_to_profile(profile_id: str, messages: List[Message]) -> Profile:
    """
    保存消息列表，并按时间戳排序，同时标记图源 Hash。
    """
    profile = get_profile(profile_id)

    # 1. 添加新消息
    profile.messages.extend(messages)

    # 2. 对整个消息列表按时间戳重新排序
    profile.messages.sort(key=lambda m: _normalize_to_utc(m.timestamp))

    # 3. 从刚刚保存的 *新消息* 中提取图源 Hash
    new_hashes_to_process = set()
    for msg in messages:
        if msg.source_image_hash and msg.source_image_hash != 'manual_entry':
            new_hashes_to_process.add(msg.source_image_hash)

    # 4. 将这些新 Hash 添加到 processed_sources
    for hash_val in new_hashes_to_process:
        if hash_val not in profile.processed_sources:
            profile.processed_sources.append(hash_val)

    # 5. 保存 Profile
    save_profile(profile)
    return profile


def add_processed_source(profile_id: str, image_hash: str):
    # 注意：此函数现在主要由 add_messages_to_profile 调用
    # 但保留它可能对未来其他功能有用
    profile = get_profile(profile_id)
    if image_hash not in profile.processed_sources:
        profile.processed_sources.append(image_hash)
        save_profile(profile)


def check_if_source_processed(profile_id: str, image_hash: str) -> bool:
    try:
        profile = get_profile(profile_id)
        return image_hash in profile.processed_sources
    except HTTPException as e:
        if e.status_code == 404:
            # 如果 Profile 不存在，自然没有处理过
            return False
        raise e


# --- 事件相关函数 ---
def add_event_to_profile(profile_id: str, event: Event) -> Profile:
    """
    添加一个新事件到 Profile，并按时间排序后保存。
    """
    profile = get_profile(profile_id)

    # 1. 添加新事件
    profile.events.append(event)

    # 2. 按时间戳排序事件列表
    profile.events.sort(key=lambda e: _normalize_to_utc(e.timestamp))

    # 3. 保存
    save_profile(profile)
    return profile


# --- Profile 管理函数 ---
def list_all_profiles() -> List[Profile]:
    """
    加载 data/profiles 目录下的所有 profile_*.json 文件
    """
    profiles = []
    search_path = os.path.join(settings.DATA_PATH, "profile_*.json")
    for filepath in glob.glob(search_path):
        try:
            profile_id = os.path.basename(filepath).replace("profile_", "").replace(".json", "")
            profiles.append(get_profile(profile_id))  # 使用 get_profile 加载和验证
        except (HTTPException, Exception) as e:
            # 跳过损坏的或加载失败的json
            print(f"Skipping invalid profile file {filepath}: {e}")
            continue
    # 按创建时间排序
    profiles.sort(key=lambda p: p.created_at, reverse=True)
    return profiles


def update_profile(profile_id: str, updates: UpdateProfileNamesRequest) -> Profile:
    """
    更新 Profile 的元数据 (例如名称)
    """
    profile = get_profile(profile_id)

    # 使用 Pydantic 的 model_dump(exclude_unset=True) 来获取有值的字段
    update_data = updates.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    # 使用 model_copy(update=...) 来安全地更新字段
    updated_profile = profile.model_copy(update=update_data)

    save_profile(updated_profile)
    return updated_profile
