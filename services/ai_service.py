from openai import OpenAI	        # 从 openai 这个库中直接导入 OpenAI 这个类（或对象）。前者用于调用 openai的 API，后者是 客户端类，用于管理这些 API
from config import (
	DEEPSEEK_API_KEY,DEEPSEEK_BASE_URL,DEEPSEEK_MODEL,
	QWEN_API_KEY,QWEN_BASE_URL,QWEN_MODEL
)

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

def ds_general_reply(chat_history):
    """
    功能：让 DeepSeek 根据上下文生成聊天回复
    参数：chat_history(历史记忆)
    """
    # 呼叫大模型思考回复
    try:
        ai_response = client_ds.chat.completions.create (         # 调用大模型 API，让它根据 chat_history 里的内容生成回复。
            model = DEEPSEEK_MODEL,
            messages = chat_history,                # messages 是 API 关键字
            temperature = 0.8
        )
        return ai_response.choices[0].message.content                # 大模型回复一般只有一个，choice[0]是选择第一个。content是固定要求
    except Exception as e:
        print(f"❌ AI 思考时崩溃了: {e}")
        return "呜呜，小夕的脑子突然卡壳了……网卡了笨蛋！"