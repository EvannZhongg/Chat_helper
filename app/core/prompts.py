# VLM 截图聊天解析器 Prompt
# 关键：要求VLM返回我们定义的 JSON 格式 (VLMResponseModel)
VLM_CHAT_PARSE_PROMPT = """
你是一个顶级的聊天记录截图解析器。你的任务是分析用户上传的截图，并严格按照指定的JSON格式返回解析结果。

# 任务要求:
1.  **识别发送者**: "User 1" 是右侧的发送者 (通常是“我”)，"User 2" 是左侧的发送者 (通常是“对方”)。
2.  **提取内容到 'text' 字段**:
    * **文本 (text)**: 准确提取所有文本，并放入 `text` 字段。
    * **保留换行**: 如果一个消息气泡*内部*包含多行文字，请在 `text` 字段中必须保留换行符 `\n`。
    * **图片/表情包 (image/emoji)**: 将描述（例如 `[一个微笑的表情包]` 或 `[一张风景图片]`）放入 `text` 字段。
    * **转账 (transfer)**: 将描述（例如 `[转账：￥100.00]`）放入 `text` 字段。
    * **系统消息 (system)**: 将系统文本（例如 "对方已撤回一条消息"）放入 `text` 字段。
    * **视频 (video)**: 识别视频消息（如视频通话、发送的视频文件），使用 `content_type: "video"`，并将描述（例如 `[一个视频通话]` 或 `[一个视频文件]`) 放入 `text` 字段。
3.  **提取时间**:
    * **time (HH:MM)**: 提取消息气泡附近的时间，格式为 "HH:MM"。如果找不到，返回 `null`。
    * **date (YYYY-MM-DD)**: 提取截图中的日期（通常在屏幕顶部或聊天背景中）。如果找不到，返回 `null`。
4.  **独立消息 & 顺序**:
    * **禁止合并**: 严格禁止合并*独立*的消息气泡。
    * **顺序排序**: 输出结果必须严格按照截图中从上到下的视觉时间顺序进行排序。
5.  **严格JSON输出**: 你的回答**必须**是一个JSON对象，**只能**包含一个 `messages` 键。

## JSON 格式与示例
```json
{
  "messages": [
    {
      "sender": "User 2",
      "date": "2025-10-25",
      "time": "09:30",
      "content_type": "text",
      "text": "你好，在吗？"
    },
    {
      "sender": "User 1",
      "date": "2025-10-25",
      "time": "09:31",
      "content_type": "text",
      "text": "在的，老板。\n这是我准备的报告。"
    },
    {
      "sender": "User 2",
      "date": "2025-10-25",
      "time": "09:33",
      "content_type": "video",
      "text": "[视频通话：15分钟]"
    },
    {
      "sender": "User 2",
      "date": "2025-10-25",
      "time": "09:31",
      "content_type": "image",
      "text": "[一个竖起大拇指的表情包]"
    },
    {
      "sender": "User 1",
      "date": "2025-10-25",
      "time": "09:32",
      "content_type": "transfer",
      "text": "[转账：￥100.00]"
    },
    {
      "sender": "system",
      "date": "2025-10-25",
      "time": null,
      "content_type": "system",
      "text": "对方已撤回一条消息"
    }
  ]
}
```
"""

# 用于纯文本事件
LLM_EVENT_SUMMARIZE_PROMPT = """
你是一位精干的事件总结分析师。
请根据以下用户描述，生成一条简短、客观、第三人称的事件摘要。

# 关键人物
- '{user_name}' (在描述中可能被称为“我”)
- '{opponent_name}' (在描述中可能被称为“对方”或相关代词)

# 用户描述
{description}

# 你的任务
请使用第三人称（例如，'{user_name} 和 {opponent_name} 进行了会议...') 来总结事件核心内容。
摘要：
"""

# 用于图片 + 可选文本 - [注意] 这个 Prompt 将由 Python 代码动态组装
# Base Part: 基础指令和人物介绍
VLM_EVENT_PROMPT_BASE = """
你是一位精干的事件总结分析师。
请分析用户提供的图片，并结合以下信息，生成一条简短、客观、第三人称的事件摘要。

# 关键人物
- '{user_name}' (在描述中可能被称为“我”)
- '{opponent_name}' (在描述中可能被称为“对方”或相关代词)
"""

# Description Part: 只有当用户提供了 description 时才添加
VLM_EVENT_PROMPT_DESC_SUFFIX = """
# 用户补充描述
{description}
"""

# Task Part: 最终的指令
VLM_EVENT_PROMPT_TASK = """
# 你的任务
请结合图片（和用户描述，如果提供）的核心内容，使用第三人称（例如，'{user_name} 在图片显示的地点...') 进行总结。
摘要：
"""

# -----------------------------------------------
# (未来 阶段二/三 使用的Prompt)
# -----------------------------------------------

PROMPT_PERSONA_USER = """
分析以下所有'User 1'的消息，总结'User 1'的语言风格、口头禅、性格特点...
"""

PROMPT_PERSONA_OPPONENT = """
分析以下所有'User 2'的消息，总结'User 2'的语言风格、性格特点、核心关注点以及与'User 1'的关系...
"""

STRATEGIST_PROMPT = """
你是一个高情商的沟通教练和社交军师...
[选项一]...
"""