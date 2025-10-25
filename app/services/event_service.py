import base64
from typing import Optional
from openai import APIError
from app.core.config import settings
# [修改] 导入新的 VLM Prompt 组件
from app.core.prompts import (
    LLM_EVENT_SUMMARIZE_PROMPT,
    VLM_EVENT_PROMPT_BASE,
    VLM_EVENT_PROMPT_DESC_SUFFIX,
    VLM_EVENT_PROMPT_TASK
)
from app.services.llm_client import llm_client, vlm_client


def get_image_base64_sync(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode('utf-8')


async def analyze_event_inputs(
        description: Optional[str],
        image_bytes: Optional[bytes],
        user_name: str,
        opponent_name: str
) -> str:
    """
    根据输入调用 LLM 或 VLM 来总结事件。
    动态构建 VLM Prompt。
    """
    description_text = description or ""  # 使用空字符串代替 "无"

    try:
        if image_bytes:
            # --- 逻辑 2 & 3: 有图片 (VLM) ---
            image_b64 = get_image_base64_sync(image_bytes)

            # 动态构建 VLM Prompt
            prompt_parts = [
                VLM_EVENT_PROMPT_BASE.format(user_name=user_name, opponent_name=opponent_name)
            ]
            if description_text:  # 只有当描述不为空时才添加
                prompt_parts.append(VLM_EVENT_PROMPT_DESC_SUFFIX.format(description=description_text))
            prompt_parts.append(VLM_EVENT_PROMPT_TASK.format(user_name=user_name, opponent_name=opponent_name))

            final_vlm_prompt = "\n".join(prompt_parts)

            completion = await vlm_client.chat.completions.create(
                model=settings.VLM_MODEL_NAME,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": final_vlm_prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }},
                    ],
                }],
                temperature=0.2
            )
            summary = completion.choices[0].message.content

        elif description_text:  # 确保 description 不为空
            # --- 逻辑 1: 纯文本 (LLM) ---
            prompt = LLM_EVENT_SUMMARIZE_PROMPT.format(
                description=description_text,
                user_name=user_name,
                opponent_name=opponent_name
            )

            completion = await llm_client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            summary = completion.choices[0].message.content

        else:
            # --- 逻辑 4: 无输入 ---
            summary = "错误：用户必须提供描述或图片才能总结事件。"

        return summary.strip()

    except APIError as e:
        print(f"Error calling model for event analysis: {e}")
        return f"模型分析失败: {e.message}"
    except Exception as e:
        print(f"Unknown error in event analysis: {e}")
        return f"未知错误: {str(e)}"