import base64
import datetime
import json
from typing import List, Tuple
from openai import APIError
from PIL import Image
import io

from app.core.config import settings
from app.core.models import Message, VLMResponseModel, VLMMessageItem, VLMUsage
from app.core.prompts import VLM_CHAT_PARSE_PROMPT
from app.services.llm_client import vlm_client


def get_image_base64(image_bytes: bytes) -> str:
    """将图片字节转换为Base64编码的字符串"""
    # 验证图片 (可选但推荐)
    try:
        Image.open(io.BytesIO(image_bytes))
    except Exception:
        raise ValueError("Invalid image file")

    return base64.b64encode(image_bytes).decode('utf-8')


def create_error_template(image_hash: str, error_msg: str) -> Message:
    """
    当VLM调用失败或返回违规内容时，创建此模板。
    满足用户需求：“可以让用户自行按照模板编辑聊天对话内容后保存”
    """
    return Message(
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        sender="system",
        content_type="system",
        text=f"VLM解析失败，请手动编辑此条目。错误: {error_msg}",
        media_description="VLM解析失败的原始截图",
        source_image_hash=image_hash,
        is_editable=True,  # 标记为可编辑
        raw_vlm_output=error_msg
    )


def process_vlm_item(item: VLMMessageItem, image_hash: str, default_date: datetime.date) -> Message:
    """
    将VLM返回的单个item转换为标准的Message对象。
    处理时间填充逻辑。
    """

    # 1. 确定日期
    if item.date:
        try:
            msg_date = datetime.date.fromisoformat(item.date)
        except ValueError:
            msg_date = default_date
    else:
        # 满足用户需求：“如果未能在图片中识别出...时间，可以捕获当前的时间进行填充”
        # 我们使用当前日期作为默认值
        msg_date = default_date

    # 2. 确定时间
    if item.time:
        try:
            msg_time = datetime.time.fromisoformat(item.time)
        except ValueError:
            msg_time = datetime.datetime.now(datetime.timezone.utc).time().replace(second=0, microsecond=0)
    else:
        msg_time = datetime.datetime.now(datetime.timezone.utc).time().replace(second=0, microsecond=0)

    # 3. 合并时间戳
    final_timestamp = datetime.datetime.combine(msg_date, msg_time, tzinfo=datetime.timezone.utc)

    return Message(
        timestamp=final_timestamp,
        sender=item.sender,
        content_type=item.content_type,
        text=item.text,
        media_description=item.description,
        source_image_hash=image_hash,
        is_editable=False  # 正常解析的消息
    )


async def parse_image_to_messages(image_bytes: bytes, image_hash: str) -> Tuple[List[Message], VLMUsage]:
    """
    调用VLM解析单张截图，返回 Message 列表 和 Token用量。
    """
    usage = VLMUsage()  # 默认用量
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

        # [新增] 记录Token消耗
        if completion.usage:
            usage = VLMUsage(
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
                total_tokens=completion.usage.total_tokens
            )

        # 1. 解析VLM返回的JSON
        try:
            vlm_data = json.loads(raw_response_text)
            parsed_response = VLMResponseModel(**vlm_data)
        except (json.JSONDecodeError, Exception) as pydantic_error:
            error_msg = f"VLM返回格式错误: {pydantic_error}. 原始输出: {raw_response_text}"
            return [create_error_template(image_hash, error_msg)], usage

        # 2. 将VLM Item转换为标准Message
        processed_messages = []
        default_date = datetime.datetime.now(datetime.timezone.utc).date()
        for item in parsed_response.messages:
            msg = process_vlm_item(item, image_hash, default_date)
            msg.raw_vlm_output = raw_response_text
            processed_messages.append(msg)

        return processed_messages, usage

    except APIError as e:
        error_msg = f"API Error: {e.code} - {e.message}"
        return [create_error_template(image_hash, error_msg)], usage
    except Exception as e:
        error_msg = f"Unknown Error: {str(e)}"
        return [create_error_template(image_hash, error_msg)], usage