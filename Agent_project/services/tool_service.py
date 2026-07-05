import json
from utils import weather_tools     # 引入你的天气工具脚本
from utils import timer_tools       # 引入定时任务工具脚本

def dispatch_tool(tool_name, arguments_str, user_id=None):      # arguments_str是ai大模型返回的 参数字符串
    """
    分发器函数：负责根据大模型给的名字和参数，自动找到对应的本地函数并执行
    """
    if tool_name not in TOOL_MAP:
        return f"错误：未找到名为 {tool_name} 的本地工具。"

    try:
        # 1. 把大模型传过来的 JSON 参数字符串，解析成 Python 字典
        args = json.loads(arguments_str)
        # 2. 拿到对应的函数对象
        func = TOOL_MAP[tool_name]

        # 拦截注入user_id，因为如果调用timer_tools工具，那么需要user_id参数
        if tool_name in ["set_timer", "set_alarm", "set_daily_alarm", "cancel_specific_alarm"]:
            args["user_id"] = user_id

        # 3. 使用 **args 把字典解包为关键字参数，动态调用函数
        # 例如：func(city="Shanghai") 相当于 weather_tools.get_weather("Shanghai")
        result = func(**args)       # 相当于 func(city="Beijing")
        return result
    except Exception as e:
        return f"本地执行工具 {tool_name} 时发生错误：{e}"


# 1. 专门定义：本地真实 Python 函数的“映射字典”
# 键名(Key)必须和大模型说明书里的 name 完全一致！
# 键值(Value)是函数对象本身（不要加括号），大模型选了谁，我们就去调谁
TOOL_MAP = {
    # weather_tools函数
    "get_weather": weather_tools.get_weather,   # 字符串：函数名
    # timer_tools函数
    "set_timer": timer_tools.set_timer,
    "set_alarm": timer_tools.set_alarm,
    "set_daily_alarm": timer_tools.set_daily_alarm,
    "cancel_specific_alarm": timer_tools.cancel_specific_alarm,
    # "get_news": news_tools.get_today_news,  # 以后扩展
}



# 2. 专门定义：给大模型看的“工具说明书”列表 (Tools Schema)，ai的api接口结构
# 以后有新工具，直接在这个列表里往后 append 字典即可
TOOL_SCHEMA = [
    # weather_tools的函数
    {
        "type": "function",     # 表示工具类型，说明是函数
        "function": {               # 功能描述
            "name": "get_weather",      # 工具调用名称
            "description": "当用户询问天气情况时调用此工具，获取指定城市的当前天气。",
            "parameters": {         # 参数描述
                "type": "object",   # 表示参数类型，参数是对象类型
                "properties": {     # 属性
                    "city": {       # 只包含city一个字段
                        "type": "string",       # 表示字段类型
                        "description": "城市名称，例如：Beijing，Shanghai，支持拼音或英文"
                    }
                },
                "required": ["city"]        # city字段必填
            }
        }
    },
    # 以后可以在这里加新工具，比如：
    # { "type": "function", "function": { "name": "get_news", ... } }
    # timer_tools的函数
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "当用户明确要求倒计时、几分钟/几小时后提醒时调用此工具（相对时间）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_minutes": {
                        "type": "integer",
                        "description": "需要等待的相对分钟数"
                    },
                    "message": {
                        "type": "string",
                        "description": "时间到了之后的提醒内容，需要符合你傲娇女友的语气。"
                    }
                },
                "required": ["delay_minutes", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_alarm",
            "description": "当用户要求在具体的绝对时间点（如今天下午3点、明天早上8点）单次提醒时调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_time": {
                        "type": "string",
                        "description": "目标时间字符串，格式为 'YYYY-MM-DD HH:MM:SS' 或 'HH:MM'。"
                    },
                    "message": {
                        "type": "string",
                        "description": "时间到了之后的提醒内容，需要符合你傲娇女友的语气。"
                    }
                },
                "required": ["target_time", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_daily_alarm",
            "description": "当用户明确要求【每天】、【日常】在某个固定时间提醒时调用此工具。如果只是一次性的，请用 set_alarm。",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_str": {
                        "type": "string",
                        "description": "每天触发的目标时间，格式必须严格为 'HH:MM'（24小时制）。"
                    },
                    "message": {
                        "type": "string",
                        "description": "时间到了之后的提醒内容，需要符合你傲娇女友的语气。"
                    }
                },
                "required": ["time_str", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_specific_alarm",
            "description": "当用户要求【取消特定的某个闹钟/提醒】时调用此工具。你需要提取出相关的事件关键词。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "想要取消的事件关键词。例如'取消喝水提醒'提取'喝水'；'关掉拉伸闹钟'提取'拉伸'。"
                    },
                    "message": {
                        "type": "string",
                        "description": "取消成功后的回复内容，需要符合你傲娇女友的语气。"
                    }
                },
                "required": ["keyword", "message"]
            }
        }
    }
]