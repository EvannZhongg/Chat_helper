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


PERSONA_OPPONENT_BASIC_EXTRACT_PROMPT = """ 你是一个信息提取助手。你的任务是从用户提供的文本中，抽取出关于某个特定人物的关键信息，并严格按照 JSON 格式返回。

任务要求
只提取事实性信息，例如：联系方式、电话、邮箱、地址、职位、公司、生日、关键背景（例如 "是xx的亲戚"）。

忽略用户的评价性、模糊性描述（例如 "他似乎很忙", "人很好"）。

返回一个 JSON 对象，键（key）是信息的类别（例如 "电话", "邮箱"），值（value）是提取到的具体内容。

如果找不到任何可提取的信息，请返回一个空 JSON 对象 {{}}。 # <-- [FIX] 修复：转义花括号

用户描述
{description}

JSON 输出
"""


PERSONA_USER_SUMMARIZE_PROMPT = """ 你是一个专业的人设（Persona）总结助手。 请根据用户提供的关于他自己的描述（可能包含性格、MBTI、沟通风格、目标等），生成一段简短、精炼、第一人称（使用“我”）的画像总结。 这段总结将用于未来提醒你（AI助手）在生成回复时要扮演“我”。

用户描述
{description}

你的总结
"""

PERSONA_EXTRACT_AND_SUMMARIZE_PROMPT = """
你是一个顶级的对话分析师和信息提取器。
你的任务是分析一段指定时间范围内的聊天记录和事件，然后严格按照 JSON 格式返回你的分析结果。

# 关键人物
- '{user_name}' (User 1 或 '用户自己')
- '{opponent_name}' (User 2 或 Event 中的 '对方')

# 任务 1：提取对方 (Opponent) 的事实信息
从 User 2 (对方) 的发言或相关事件中，提取所有*事实性*信息（例如：提到的具体地点、时间、人物、联系方式、职位、公司、喜好、承诺等）。
- 忽略闲聊和情绪化表达。
- 将结果格式化为键值对。

# 任务 2：总结这段时间内的互动
基于双方的对话和发生的事件，精炼总结这段时间内的核心互动内容、情绪氛围以及（如果有的话）关键的未决事项。

# 输入数据 (聊天记录与事件)
{chat_log}

# 严格的 JSON 输出格式
请*只*返回一个 JSON 对象，必须包含 `extracted_info` 和 `summary` 两个键。

## 示例
{{
  "extracted_info": {{
    "家庭住址": "似乎在XX小区",
    "承诺": "下周三之前给答复",
    "喜好": "喜欢喝拿铁"
  }},
  "summary": "{opponent_name} 在这段时间内情绪不高，主要讨论了项目A的延期问题。{user_name} 进行了安抚，但 {opponent_name} 承诺的下周三答复是关键跟进点。"
}}
"""

PROMPT_PERSONA_USER = """ 分析以下所有'User 1'的消息，总结'User 1'的语言风格、口头禅、性格特点... """

PROMPT_PERSONA_OPPONENT = """ 分析以下所有'User 2'的消息，总结'User 2'的语言风格、性格特点、核心关注点以及与'User 1'的关系... """

STRATEGIST_PROMPT = """ 你是一个高情商的沟通教练和社交军师... [选项一]... """