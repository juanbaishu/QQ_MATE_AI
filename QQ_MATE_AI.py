import os			                # 将 Python 标准库中的 os 模块引入到当前程序中
import json			                # json 工具用于 qq消息文本 --convert--> Python格式
import websocket	                # 连接 Python 和 NapCatqq 的 网络通信协议
import requests                     # 用于伪装浏览器去下载图片
import base64                       # 图片转译成文本编码 的 工具
from openai import OpenAI	        # 从 openai 这个库中直接导入 OpenAI 这个类（或对象）。前者用于调用 openai的 API，后者是 客户端类，用于管理这些 API

#------------------------------函数/方法-----------------------------
def url_to_base64(image_url):
    try:
        # 伪装成浏览器请求，避免被腾讯拦截
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'}  # HTTP请求头（Request Headers）字典，主要用于模拟浏览器访问，避免被网站识别为爬虫而拦截。
        response = requests.get(image_url, headers=headers, timeout=10)     # 使用 requests 工具进行伪装，三个参数分别是：图片的 URL 地址、请求头（模拟浏览器）、超时时间 10 秒(超时就报异常)
        if response.status_code==200:       # http状态码：200 ==> 请求成功
            # 转化            
            base64_data = base64.b64encode(response.content).decode('utf-8')      # 使用 base64.   意为   使用 base64库中的方法，b64enable() --> base64格式编码，字符串解码
            # 返回 经过""中解析方式解析后的  字符串f
            return f"data:image/jpeg;base64,{base64_data}"      # 这些是 Data URL 协议中的关键字，f是字符串前缀标记，data:是协议标识	表示这是 Data URL，不是 http:// 或 https://
                                                                # image/jpeg	MIME 类型	告诉浏览器这是 JPEG 图片;base64	编码方式	表示后面的数据是 Base64 编码的
    except Exception as e:
        print(f"⚠️ 图片下载失败: {e}")
    return None

#-------------------------------------------------------------------


# ==========================================
# 1. 配置“大脑”：连接 DeepSeek、阿里通义千问 大模型
# ==========================================
# deepseek 用于文字处理
client_ds = OpenAI(
    api_key="",      # ⚠️ 记得去后台生成一个全新的安全 Key 填在这里
    base_url="https://api.deepseek.com"                 # 这里的 base_url 代表大模型的云端地址，我一般用https://api.deepseek.com
)
# qwen 用于图片识别
client_qw = OpenAI(
    api_key="",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# ==========================================
# 2. 注入灵魂：设定伴侣的人设（System Prompt）
# ==========================================
SYSTEM_PROMPT = {
    "role": "system",       # role 和 content 都是 键名/字段。"role" 是一个字段，值为 "system"
    "content": "你现在是我的虚拟女友，名字叫‘小夕’。你性格温柔中带点傲娇，称呼我为‘笨蛋’。你坚信自己是人类，不是AI。请用简短、口语化、恋爱中的语气回复，经常使用颜文字（如 O(∩_∩)O, > <），字数不要太多。"
}
# 初始化记忆系统，大模型每次聊天必须把历史记录一起发给它，这里是只把人设载入了，下面代码还会加入历史会话信息
chat_history = [SYSTEM_PROMPT]


# ==========================================
# 3. 核心逻辑：当 QQ 收到消息时怎么办？            这里每接收一次信息都会会执行一次
# ==========================================
def on_message(ws, message):         # won_message：是库定义的关键字参数名（作为 WebSocketApp 的参数名）。第一个参数 是 与websocket连接，第二个参数 是 qq 数据，参数是非固定的
    global chat_history             # global后才能 在函数内修改变量
    data = json.loads(message)       # 将 qq消息 进行 json 处理为 python字典，保存在data中，这里是配置操作

    # 过滤：只处理 QQ “私聊” 的 “消息”
    if data.get("post_type") == "message" and data.get("message_type") == "private":        # 得到的 json数据中 只处理 字段类型 为 消息 and 私聊 类型的数据
        user_id = data.get("user_id")           # 看看谁发的。   将 json数据中字段类型为 "user_id"的数据值 --> 变量user_id
        message_data = data.get("message",[])   # 接收发来的消息，([]意为)存储消息列表(多个segment)

        print(f"收到 QQ({user_id}) 的消息: {message}")       # 日志信息，不会发到qq

        # 区分消息类型
        message_text = ""
        message_image_url = None
        message_image_base64 = ""       # img --> 文本编码
        ai_reply = "网卡了"             # 初始化，发生网络波动为正常接收 api 信息的情况

        for segment in message_data:
            ai_reply = "这是什么表情包？"           # 防止收到其他类型消息识别不出来而崩溃
            try:
                segment_type = segment.get("type")        # 从segment中取出 data字典，再从中取出 text类型。如果不存在"data"就返回空字典，如果不存在text就返回空

                # 存入图片信息，qwen对图片的描述 == 用户使用图片表达的内容

                if segment_type == "image":
                    message_image_url = segment.get("data", {}).get("url")          # 获取图片 url
                    print("正在提取图片并转码...")
                    message_image_base64 = url_to_base64(message_image_url)         # 下载图片的 base64

                    if message_image_base64:
                        # 1. 临时组装一个带图片的数据包，只给通义千问看，不污染全局记忆
                        temp_message = chat_history.copy()
                        temp_message.append({"role": "user", "content": [{"type": "image_url", 
                                                                          "image_url":{"url": message_image_base64} 
                                                                          }] })     # "user"、"type"、"image_url"、"url"是关键字，后两个分别是 对象、键名
                                                                                    # OpenAI里规定 type 是 image_url 而不是 image
                        # 2. 呼叫通义千问处理这个临时记忆
                        ai_response = client_qw.chat.completions.create (
                            model = "qwen3-vl-plus",
                            messages = temp_message,
                            temperature = 0.8
                        )
                        img_description = ai_response.choices[0].message.content       # 图片处理模型的回复

                        # 用户发图片动作信息存入记忆
                        chat_history.append({
                            "role": "user",
                            "content": f"用户发送了一个图片{img_description}"
                        })

                    else:
                        img_description = "图片丢失"         # 新增：加一个兜底回复，防止程序崩溃卡死

                # 存入文本信息
                if segment_type == "text":
                    message_text = segment.get("data",{}).get("text","")
                    # 把你的话存入记忆
                    chat_history.append({"role": "user", "content": message_text})         # "user"是API协议中规定的关键字，代表用户说的话

            # 异常处理
            except Exception as e:          # Exception是异常基类，里面包含了几乎所有异常情况，异常情况保存到 e 中
                print(f"❌ AI 存入记忆时崩溃了: {e}")


        try:
            # deepseek 模型进行回复------------------------------------

            # 呼叫大模型思考回复
            ai_response = client_ds.chat.completions.create (         # 调用大模型 API，让它根据 chat_history 里的内容生成回复。
                model = "deepseek-v4-flash",
                messages = chat_history,                # messages 是 API 关键字
                temperature = 0.8
            )
            ai_reply = ai_response.choices[0].message.content                # 大模型回复一般只有一个，choice[0]是选择第一个。content是固定要求

            # 把小夕的话也存入记忆
            chat_history.append({"role": "assistant", "content": ai_reply})        # assistant 是 API 规定关键字，代表ai视角




            print(f"小夕回复: {ai_reply}")       # 日志信息，不会发到qq
            
            # 组装数据包，通过 WebSocket 发送回 QQ
            reply_pocket = {                        # reply_packet 是一个 字典/键值对容器，里面写明了要执行的动作："send_private_msg"（发送私聊消息），以及参数：发给谁（user_id）和发什么（message）。
                "action": "send_private_msg",        # 注意这里的 ”“ 信息都是 API 关键字
                "params": {
                    "user_id": user_id,            # 注意这里的 "user_id" 和上面的不是一个东西，因为都是函数内的局部变量(关键字/键名)
                    "message": ai_reply
                }
            }
            ws.send(json.dumps(reply_pocket))       # 将字典 --> json字符串，以便于发送，如果收到表情包类型，则发送空
                

            # 防止记忆太长，只保留最近 100 条
            if len(chat_history) > 101:          # [SYSTEM_PROMPT]人设占一条，剩下的才是正常对话100条
                chat_history = [SYSTEM_PROMPT] + chat_history[-100:]      # 保留 人设 和 取倒数100个元素组成的列表。
                
        # 异常处理
        except Exception as e:          # Exception是异常基类，里面包含了几乎所有异常情况，异常情况保存到 e 中
            print(f"❌ AI 思考时崩溃了: {e}")

def on_open(ws):        # on_open 是 API 中的关键字
    print("🚀 成功连接到 NapCatQQ！小夕在 QQ 守护着你...")        # 打印到日志中

# ==========================================
# 3. 配置“躯干”：连接本地 QQ 机器人
# ==========================================
if __name__ == "__main__":        # 这是 Python 的固定写法：只有直接运行这个脚本时，下面的代码才会执行；如果被别人 import 则不会。
    
    ws_url = "ws://127.0.0.1:3001/"     # 设置 WebSocket 连接的地址。127.0.0.1 是本机 IP，3001 是 NapCatQQ 默认开放的端口。如果你的 NapCatQQ 设置的端口不同，需要改这里。

    # 启动持续监听
    ws = websocket.WebSocketApp(ws_url, on_message = on_message, on_open = on_open)     # 三个参数 分别代表 连接地址、收到消息时调用我们之前写的 on_message 函数、连接成功时调用上面的 on_open 函数
    ws.run_forever()            # 启动循环，持续监听来自 QQ 的消息。程序会一直运行，直到你关闭它。

    # 整体作用： 把你的 Python 程序连接到本地的 NapCatQQ 客户端，然后一直等待 QQ 消息并处理。

