import logging
import copy         # 引入深拷贝
from openai import OpenAI           # 从 openai 这个库中直接导入 OpenAI 这个类（或对象）。前者用于调用 openai的 API，后者是 客户端类，用于管理这些 API
from config import (
    DEEPSEEK_API_KEY,DEEPSEEK_BASE_URL,DEEPSEEK_MODEL,
    QWEN_API_KEY,QWEN_BASE_URL,QWEN_MODEL
)
from services import memory_service
from services.tool_service import TOOL_SCHEMA, dispatch_tool
from datetime import datetime


# 1. 初始化两个大模型的客户端
client_ds = OpenAI(api_key=DEEPSEEK_API_KEY,base_url=DEEPSEEK_BASE_URL)
client_qw = OpenAI(api_key=QWEN_API_KEY,base_url=QWEN_BASE_URL)

def qw_describe_img(image_base64):
    """
    功能：让通义千问看图并返回描述，描述代替图片进入记忆
    参数：image_base64(图片的base64编码)
    """
    img_message = [{"role": "user", 
                    "content": [{"type": "text", "text": "请用一句话简要、客观地描述这张图片里有什么内容，不需要任何寒暄、称呼或聊天语气。" },
                                 {"type":"image_url", "image_url":{"url": image_base64}} ] }]     # "user"、"type"、"image_url"、"url"是关键字，后两个分别是 对象、键名
                                                                    # OpenAI里规定 type 是 image_url 而不是 image
    # 呼叫通义千问处理这个临时记忆
    try:
        ai_response = client_qw.chat.completions.create (
            model = QWEN_MODEL,
            messages = img_message,
            temperature = 0.2           # 降低温度 --> 更严谨
        )
        return ai_response.choices[0].message.content       # 图片处理模型的回复
    except Exception as e:      # error
        print(f"⚠️ 图片识别失败: {e}")
        return None

def ds_general_reply(user_id, chat_history):
    """
    功能：让 DeepSeek 根据上下文生成聊天回复，具备自主调用工具能力
    参数：chat_history(历史记忆)
    """
    try:
        # 定时任务，需要记忆中包含时间，但是直接加会污染记忆库，所以这里用 temp_history
        temp_history = copy.copy(chat_history)
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        temp_history.insert(1, {
            "role": "system",
            "content": f"【系统当前绝对时间：{current_time_str}】。如果用户提到今天、明天、下午等时间，请以此时间为基准推算。"
            f"【最高指令】：调用工具时，必须 100% 严格使用工具说明书中定义的参数名称（如 time_str, target_time），绝对禁止自行发明或修改参数名！"
        })

        # 第一趟：这里判断需要调用那些 工具函数，带着工具箱去问大模型
        ai_response_first = client_ds.chat.completions.create (
            model = DEEPSEEK_MODEL,
            messages = temp_history,
            tools = TOOL_SCHEMA,               # 把工具箱说明书喂给大模型
            tool_choice = "auto",             # 让大模型自主决定用不用工具
            temperature = 0.2
        )
        response_message_first = ai_response_first.choices[0].message


        # ==========================================================
        # 分支一：【工具调用流】如果大模型说“我要用工具”（比如查天气）
        # ==========================================================

        # 判断：大模型是否要求用工具？
        if response_message_first.tool_calls:
            # 1. 存入大模型的思考意图
            memory_service.add_tool_request_to_history(response_message_first)

            # 2. 依次调用工具查数据
            for tool_call in response_message_first.tool_calls:
                t_name = tool_call.function.name
                t_args = tool_call.function.arguments       # 这是一个包含参数的 JSON 字符串
                logging.info(f"⚙️ 小夕调用工具: {t_name} -> 参数: {t_args}")
                tool_result = dispatch_tool(t_name, t_args, user_id=user_id)        # 自动执行工具函数的分发器

                # 3. 从tool视角(默认值就是)，存入真实的工具结果
                memory_service.add_tool_result_to_history(     # 调用函数，传入形参
                    tool_call_id = tool_call.id,
                    tool_name = t_name,
                    result_text = tool_result
                )

            # 4. 第二趟：大模型看着刚查到的数据，重新组织语言回复
            logging.info(" -> 小夕已获得真实数据，正在组织语言中...")
            ai_response_second = client_ds.chat.completions.create (
                model = DEEPSEEK_MODEL,
                messages = memory_service.get_history(),
                temperature = 0.8
            )
            response_message_second = ai_response_second.choices[0].message.content
            return response_message_second

        # ==========================================================
        # 分支二：【纯纯闲聊流】如果大模型觉得不需要用工具
        # ==========================================================
        else:
            return response_message_first.content


    except Exception as e:
        logging.error(f"❌ AI 思考时崩溃了: {e}")
        return "呜呜，小夕的脑子突然卡壳了……网卡了笨蛋！"
