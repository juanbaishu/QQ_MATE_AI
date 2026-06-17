import json
from utils import weather_tools		# 引入你的天气工具脚本

# 1. 专门定义：给大模型看的“工具说明书”列表 (Tools Schema)
# 以后有新工具，直接在这个列表里往后 append 字典即可
TOOL_SCHEMA = [
	{
		"type": "function",		# 表示工具类型，说明是函数
		"function": {				# 功能描述
			"name": "get_weather",		# 工具调用名称
			"description": "当用户询问天气情况时调用此工具，获取指定城市的当前天气。",
			"parameters": {			# 参数描述
				"type": "object",	# 表示参数类型，参数是对象类型
				"properties": {		# 属性
					"city": {		# 只包含city一个字段
						"type": "string",		# 表示字段类型
						"description": "城市名称，例如：Beijing，Shanghai，支持拼音或英文"
					}
				},
				"required": ["city"]		# city字段必填
			}
		}
	}
	# 以后可以在这里加新工具，比如：
    # { "type": "function", "function": { "name": "get_news", ... } }
]

# 2. 专门定义：本地真实 Python 函数的“映射字典”
# 键名(Key)必须和大模型说明书里的 name 完全一致！
# 键值(Value)是函数对象本身（不要加括号），大模型选了谁，我们就去调谁
TOOL_MAP = {
	"get_weather": weather_tools.get_weather,	# 字符串：函数名
	# "get_news": news_tools.get_today_news,  # 以后扩展
}

def dispatch_tool(tool_name, arguments_str):
	"""
	分发器函数：负责根据大模型给的名字和参数，自动找到对应的本地函数并执行
	"""
	if tool_name not in TOOL_MAP:
		return f"错误：未找到名为 {tool_name} 的本地工具。"

	try:
		# 1. 把大模型传过来的 JSON 字符串参数，解析成 Python 字典
		args = json.loads(arguments_str)
		# 2. 拿到对应的函数对象
		func = TOOL_MAP[tool_name]
		# 3. 使用 **args 把字典解包为关键字参数，动态调用函数
		# 例如：func(city="Shanghai") 相当于 weather_tools.get_weather("Shanghai")
		result = func(**args)		# 相当于 func(city="Beijing")
		return result
	except Exception as e:
		return f"本地执行工具 {tool_name} 时发生错误：{e}"