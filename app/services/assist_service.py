# app/services/assist_service.py
import json
import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
from zoneinfo import ZoneInfo
from collections import defaultdict # [!!] 导入 defaultdict
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

# 导入 LLM 客户端、配置和核心 Prompt
from app.services.llm_client import llm_client
from app.core.config import settings
from app.core.prompts import STRATEGIST_PROMPT # [!!] 将使用更新后的 Prompt

# 导入数据服务和模型
from app.services import profile_service
from app.core.models import Message, Event, Profile, ContextualInsight # [!!] 导入 ContextualInsight

# 导入工具 (不变)
from app.services.assist_tools import available_tools

# 本地时区 (不变)
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

# 工具定义 (不变, 使用 dates 列表获取聊天记录)
tools_definitions: List[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "get_opponent_persona_details",
            "description": "获取对方(Opponent)的完整画像信息，包括基础信息(basic_info)和聊天分析(chat_analysis)。当需要了解对方背景、联系方式或详细性格分析时调用。",
            "parameters": {"type": "object", "properties": {}}
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_chat_history",
            "description": "获取指定日期列表的详细聊天记录(Messages)。当摘要信息不够，且你需要查看特定某几天的对话细节时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dates": {
                        "type": "array",
                        "description": "一个包含 'YYYY-MM-DD' 格式日期字符串的列表。例如: ['2025-10-26', '2025-10-24']",
                        "items": {"type": "string", "format": "date"}
                    }
                },
                "required": ["dates"],
            },
        },
    },
    {  # get_recent_events (不变)
        "type": "function", "function": {"name": "get_recent_events",
                                         "description": "获取最近N天的详细离线事件(Events)。当摘要信息不够时使用。",
                                         "parameters": {"type": "object", "properties": {
                                             "days": {"type": "integer", "description": "要获取的最近天数，默认为7",
                                                      "default": 7}}, "required": []}}},
    {  # search_insights_by_keyword (不变)
        "type": "function", "function": {"name": "search_insights_by_keyword",
                                         "description": "根据关键词搜索 *所有* 历史洞察(Insights)的摘要。用于查找特定历史主题。",
                                         "parameters": {"type": "object", "properties": {"keyword": {"type": "string",
                                                                                                     "description": "用于搜索摘要的关键词 (例如 '项目A')"}},
                                                        "required": ["keyword"]}}},
]


class AssistService:
    """
    管理“社交军师” Agent 的核心服务。(初始化不变)
    """
    def __init__(self, profile_id: str, user_name: str, opponent_name: str):
        self.profile_id = profile_id
        self.user_name = user_name
        self.opponent_name = opponent_name
        self.messages: List[ChatCompletionMessageParam] = []

    # --- [!!! 修改此函数 !!!] ---
    def _build_initial_context(self, k_insights: int = 5) -> str:
        """
        [修改后] 构建第一轮需要的初始上下文。
        包含：当前日期、用户画像、对方分析、
        【今天】的详细日志 + 【上一个活动日】的详细日志（如果今天有活动）
        或 【最近活动日】的详细日志（如果今天没活动）、
        近期K个带日期的摘要。
        """
        try:
            # --- 0. 准备工作 ---
            current_datetime_local = datetime.datetime.now(LOCAL_TZ)
            today_date = current_datetime_local.date()
            current_date_str = today_date.isoformat()

            # --- 1. 加载基础画像和摘要 (不变) ---
            user_persona = profile_service.load_user_persona(self.profile_id)
            opponent_persona = profile_service.load_opponent_persona(self.profile_id)
            opponent_analysis_summary = (
                opponent_persona.chat_analysis if opponent_persona and opponent_persona.chat_analysis else " (暂无沟通风格分析)")
            insights = profile_service.load_insights(self.profile_id)
            insights.sort(key=lambda x: x.analysis_date, reverse=True)
            recent_insights = insights[:k_insights]

            # --- 2. 加载聊天和事件数据 ---
            all_items_map = defaultdict(list)
            latest_data_date: Optional[datetime.date] = None
            previous_data_date: Optional[datetime.date] = None
            sorted_dates_with_data = []

            try:
                profile = profile_service.get_profile(self.profile_id)
                all_raw_items: List[Union[Message, Event]] = profile.messages + profile.events
                if all_raw_items:
                    # 按日期分组
                    for item in all_raw_items:
                        item_local_date = item.timestamp.astimezone(LOCAL_TZ).date()
                        all_items_map[item_local_date].append(item)

                    # 获取有数据的日期并排序 (最新在前)
                    sorted_dates_with_data = sorted(all_items_map.keys(), reverse=True)
                    if sorted_dates_with_data:
                        latest_data_date = sorted_dates_with_data[0]
                        if len(sorted_dates_with_data) > 1:
                            previous_data_date = sorted_dates_with_data[1]

            except Exception as e:
                print(f"Error loading profile items for context: {e}")
                # 出错不影响继续，只是日志部分会显示错误信息

            # --- 3. 内部函数：获取并格式化指定日期的日志 ---
            def _get_log_for_date(target_date: Optional[datetime.date]) -> Tuple[Optional[datetime.date], str]:
                if target_date is None or target_date not in all_items_map:
                    return target_date, "(无记录)"

                items_for_day = all_items_map[target_date]
                items_for_day.sort(key=lambda x: x.timestamp)  # 按时间排序

                log_entries = []
                for item in items_for_day:
                    local_time_str = item.timestamp.astimezone(LOCAL_TZ).strftime('%H:%M')
                    entry = ""
                    if isinstance(item, Message):
                        sender_name = "System"
                        if item.sender == "User 1":
                            sender_name = self.user_name
                        elif item.sender == "User 2":
                            sender_name = self.opponent_name
                        entry = f"[{local_time_str}] {sender_name}: {item.text or ''} (Type: {item.content_type})"
                    elif isinstance(item, Event):
                        entry = f"[{local_time_str}] [!! 离线事件 !!]: {item.summary}"
                    if entry:
                        log_entries.append(entry)

                return target_date, "\n".join(log_entries) if log_entries else "(当天无有效记录)"

            # --- 4. 获取需要的详细日志 ---
            today_log_date, today_log = _get_log_for_date(today_date)

            complementary_log_date: Optional[datetime.date] = None
            complementary_log: str = ""
            complementary_log_label: str = ""

            if today_date in all_items_map:  # 如果今天有活动
                # 获取今天之前的最近活动日日志
                complementary_log_date, complementary_log = _get_log_for_date(previous_data_date)
                complementary_log_label = f"上一个活动日 ({complementary_log_date.isoformat() if complementary_log_date else 'N/A'}) 的详细日志:"
            else:  # 如果今天没活动
                # 获取最近活动日的日志
                complementary_log_date, complementary_log = _get_log_for_date(latest_data_date)
                complementary_log_label = f"最近活动日 ({complementary_log_date.isoformat() if complementary_log_date else 'N/A'}) 的详细日志:"

            # --- 5. 格式化 Insight 摘要 (带日期) ---
            insights_summary_with_dates = []
            if recent_insights:
                for insight in recent_insights:
                    # [!!] 添加日期
                    insights_summary_with_dates.append(f"[{insight.analysis_date.isoformat()}]: {insight.summary}")
            insights_formatted = "\n".join(insights_summary_with_dates) if insights_summary_with_dates else " (暂无)"

            # --- 6. 组装最终上下文 ---
            context_parts = [
                "--- 初始上下文 ---",
                f"今天是: {current_date_str}",
                "\n1. 我的画像 (User Persona):",
                (user_persona.model_dump_json(indent=2, exclude={'profile_id'}) if user_persona else " (暂无)"),
                "\n2. 对方沟通风格分析 (Opponent Chat Analysis):",
                opponent_analysis_summary,
                f"\n3. 今天 ({today_date.isoformat()}) 的详细日志:",  # [!!] 包含今天的日志
                today_log,
                f"\n4. {complementary_log_label}",  # [!!] 包含补充日志 (昨天或最近)
                complementary_log,
                f"\n5. 更早 ({len(recent_insights)} 条) 的互动摘要 (Insights):",  # [!!] 更新序号和描述
                insights_formatted,  # [!!] 使用带日期的摘要
                "--- 初始上下文结束 ---",
                "\n提示: 如果你需要了解对方的基础信息（如电话、职位、背景），请使用 `get_opponent_persona_details` 工具查询。如果需要查看【今天】或【补充日志】之外的其他日期的详细聊天记录，请使用 `get_recent_chat_history` 工具查询。"
                # [!!] 更新提示
            ]
            return "\n".join(context_parts)

        except Exception as e:
            print(f"Error building context for {self.profile_id}: {e}")
            import traceback
            traceback.print_exc()  # 打印详细错误
            return f"Error building context: {e}"

    # --- ReAct 循环 (get_assistance 函数保持不变) ---
    async def get_assistance(
            self,
            opponent_message: str,
            user_thoughts: str,
            max_loops: int = 5
    ) -> Dict[str, Any]:
        """
        执行完整的 ReAct 循环以获取辅助建议。(内部逻辑保持不变)
        """
        # ... (代码完全不变, 它会调用上面修改后的 _build_initial_context) ...
        initial_context = self._build_initial_context()
        formatted_system_prompt = STRATEGIST_PROMPT.format(user_name=self.user_name, opponent_name=self.opponent_name)
        self.messages = [{"role": "system", "content": formatted_system_prompt},
                         {"role": "system", "content": initial_context}]
        user_input = f"""\n--- 用户求助 ---\n[对方的最新消息]: {opponent_message}\n[我内心的真实想法]: {user_thoughts}\n--- 请开始分析 ---"""
        self.messages.append({"role": "user", "content": user_input})

        loop_count = 0
        while loop_count < max_loops:
            loop_count += 1
            print(
                f"[AssistService] Loop {loop_count} for {self.profile_id}. Sending {len(self.messages)} messages to LLM.")
            try:
                response = await llm_client.chat.completions.create(
                    model=settings.LLM_MODEL_NAME, messages=self.messages, tools=tools_definitions,
                    tool_choice="auto", temperature=0.5, response_format={"type": "json_object"})
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                if tool_calls:
                    print(
                        f"[AssistService] Loop {loop_count}: LLM requests tool calls: {[t.function.name for t in tool_calls]}")
                    self.messages.append(response_message)
                    for tool_call in tool_calls:
                        # ... (工具调用执行逻辑不变) ...
                        function_name = tool_call.function.name
                        function_to_call = available_tools.get(function_name)
                        function_response_str = ""
                        if function_to_call:
                            try:
                                function_args = json.loads(tool_call.function.arguments)
                                function_args["profile_id"] = self.profile_id
                                function_response_str = function_to_call(**function_args)
                            except Exception as e:
                                print(f"Error executing tool {function_name}: {e}")
                                function_response_str = json.dumps({"error": f"Tool execution failed: {e}"})
                        else:
                            function_response_str = json.dumps({"error": f"Tool '{function_name}' not found."})
                        self.messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name,
                                              "content": function_response_str})
                    continue
                else:
                    # ... (最终回复处理逻辑不变) ...
                    print(f"[AssistService] Loop {loop_count}: LLM provides Final Answer.")
                    try:
                        final_result = json.loads(response_message.content)
                        if "strategy_analysis" in final_result and "reply_options" in final_result:
                            return final_result
                        else:
                            return {"error": f"LLM 最终回复 JSON 缺少必要字段: {response_message.content}"}
                    except json.JSONDecodeError as e:
                        return {"error": f"LLM 最终回复不是有效的 JSON: {response_message.content}"}
            except Exception as e:
                print(f"Error during LLM call in AssistService: {e}")
                import traceback;
                traceback.print_exc()
                return {"error": f"Agent 循环出错: {e}"}
        # 5. 处理循环超时
        print(f"Error: Agent reached max loops ({max_loops}) for profile {self.profile_id}")
        return {"error": "Agent 思考超时 (已达最大循环次数)"}