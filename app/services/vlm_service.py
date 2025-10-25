import base64
import datetime
import json
from typing import List, Tuple
from openai import APIError
from PIL import Image
import io

from app.core.config import settings
# [修改] 导入 VLMUsage
from app.core.models import Message, VLMResponseModel, VLMMessageItem, VLMUsage
from app.core.prompts import VLM_CHAT_PARSE_PROMPT
from app.services.llm_client import vlm_client

# 定义 CST 时区 (UTC+8) - 根据您的实际时区调整
# 如果需要更灵活的时区处理，未来可以考虑 pytz 或 zoneinfo
CST_TZ = datetime.timezone(datetime.timedelta(hours=8))


def get_image_base64(image_bytes: bytes) -> str:
    # ... (此函数保持不变) ...
    try:
        Image.open(io.BytesIO(image_bytes))
    except Exception:
        raise ValueError("Invalid image file")
    return base64.b64encode(image_bytes).decode('utf-8')


def create_error_template(image_hash: str, error_msg: str) -> Message:
    # ... (此函数保持不变, 已确保使用 aware time) ...
    return Message(
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        sender="system",
        content_type="system",
        text=f"VLM解析失败，请手动编辑此条目。错误: {error_msg}",
        source_image_hash=image_hash,
        is_editable=True,
        raw_vlm_output=error_msg,
        auto_filled_date=True,
        auto_filled_time=True
    )


# [修改] 重写 process_vlm_item 的时间逻辑
def process_vlm_item(item: VLMMessageItem, image_hash: str) -> Message:
    """
    将VLM返回的单个item转换为标准的Message对象。
    处理时间填充逻辑，假定VLM时间为本地时区(CST)，并转换为UTC存储。
    """

    # 1. 获取当前的本地时间和日期 (用于填充)
    now_local = datetime.datetime.now(CST_TZ)
    today_date_local = now_local.date()
    now_time_local = now_local.time().replace(second=0, microsecond=0)

    # 2. 解析 VLM 返回的日期和时间
    msg_date = None
    msg_time = None
    date_parsed_ok = False
    time_parsed_ok = False
    auto_filled_date = False
    auto_filled_time = False

    if item.date:
        try:
            msg_date = datetime.date.fromisoformat(item.date)
            date_parsed_ok = True
        except (ValueError, TypeError):
            pass  # 解析失败，将使用填充值

    if item.time:
        try:
            # 尝试解析 HH:MM 或 HH:MM:SS
            if len(item.time) == 5:  # HH:MM
                msg_time = datetime.time.fromisoformat(item.time + ":00")
            else:  # 假设是 HH:MM:SS 或其他ISO格式
                msg_time = datetime.time.fromisoformat(item.time)
            time_parsed_ok = True
        except (ValueError, TypeError):
            pass  # 解析失败，将使用填充值

    # 3. 按需填充
    if not date_parsed_ok:
        msg_date = today_date_local
        auto_filled_date = True

    if not time_parsed_ok:
        msg_time = now_time_local
        auto_filled_time = True

    # 4. 组合成一个 Naive (朴素) 的本地时间 datetime 对象
    #    如果时间部分解析失败，秒和微秒会被设为0
    #    我们需要确保 msg_time 总是 datetime.time 类型
    if not isinstance(msg_time, datetime.time):
        msg_time = now_time_local  # 备用填充

    final_timestamp_naive_local = datetime.datetime.combine(msg_date, msg_time)

    # 5. [核心] 假定这个 Naive 时间是本地时区(CST)，并显式添加时区信息
    final_timestamp_aware_local = final_timestamp_naive_local.replace(tzinfo=CST_TZ)

    # 6. [核心] 将本地时区时间转换为 UTC 时间进行存储
    final_timestamp_utc = final_timestamp_aware_local.astimezone(datetime.timezone.utc)

    return Message(
        timestamp=final_timestamp_utc,  # 保存 UTC 时间
        sender=item.sender,
        content_type=item.content_type,
        text=item.text,
        source_image_hash=image_hash,
        is_editable=False,
        auto_filled_date=auto_filled_date,
        auto_filled_time=auto_filled_time
    )


async def parse_image_to_messages(image_bytes: bytes, image_hash: str) -> Tuple[List[Message], VLMUsage]:
    """
    调用VLM解析单张截图，返回 Message 列表 和 Token用量。
    """
    usage = VLMUsage()
    try:
        image_b64 = get_image_base64(image_bytes)

        completion = await vlm_client.chat.completions.create(
            model=settings.VLM_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VLM_CHAT_PARSE_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            },
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        raw_response_text = completion.choices[0].message.content

        print("\n" + "=" * 50)
        print(f"[VLM Service] Received raw JSON from model ({settings.VLM_MODEL_NAME}):")
        print(raw_response_text)
        print("=" * 50 + "\n")

        if completion.usage:
            usage = VLMUsage(
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
                total_tokens=completion.usage.total_tokens
            )

        try:
            vlm_data = json.loads(raw_response_text)
            parsed_response = VLMResponseModel(**vlm_data)
        except (json.JSONDecodeError, Exception) as pydantic_error:
            error_msg = f"VLM返回格式错误: {pydantic_error}. 原始输出: {raw_response_text}"
            return [create_error_template(image_hash, error_msg)], usage

        processed_messages = []
        for item in parsed_response.messages:
            # [修改] 调用更新后的 process_vlm_item
            msg = process_vlm_item(item, image_hash)
            msg.raw_vlm_output = raw_response_text
            processed_messages.append(msg)

        return processed_messages, usage

    except APIError as e:
        error_msg = f"API Error: {e.code} - {e.message}"
        return [create_error_template(image_hash, error_msg)], usage
    except Exception as e:
        error_msg = f"Unknown Error: {str(e)}"
        return [create_error_template(image_hash, error_msg)], usage
