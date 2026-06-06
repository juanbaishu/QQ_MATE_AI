# 主程序控制中心
import os			                # 将 Python 标准库中的 os 模块引入到当前程序中
import json			                # JavaScript 格式，最通用的文本格式
import websocket	                # 连接 Python 和 NapCatqq 的 网络通信协议
import requests                     # 用于伪装浏览器去下载图片
import base64                       # 图片转译成文本编码 的 工具

import logging
# ==========================================
# 日志系统配置
# ==========================================
logging.basicConfig(
    level=logging.INFO,  # 记录的最低级别，INFO及以上的都会被记录
    format='%(asctime)s [%(levelname)s] %(message)s',  # 日志格式：时间 [级别] 消息内容
    datefmt='%Y-%m-%d %H:%M:%S',  # 时间格式
    handlers=[
        logging.FileHandler("logs/ai_bot.log", encoding="utf-8", mode='a'),  # 1. 写入到文件 (a表示追加模式)
        logging.StreamHandler()  # 2. 同时输出到黑色控制台
    ]
)

# 从拆分出来的文档中，导入需要的工具
from config import WS_URL
#from ai_service import qw_describe_img, ds_general_reply		# 定义的两个方法
from services import ai_service
from services import memory_service

# ------------------------------工具函数-----------------------------
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
        logging.info(f"⚠️ 图片下载失败: {e}")
        return None

# ==========================================
# 核心逻辑：当 QQ 收到私聊消息时
# ==========================================
def on_message(ws, message):
    data = json.loads(message)       # 将 qq消息 进行 json 处理为 python字典，保存在data中，这里是配置操作
   
     # 过滤：只处理 QQ “私聊” 的 “消息”
    if data.get("post_type") == "message" and data.get("message_type") == "private":        # 得到的 json数据中 只处理 字段类型 为 消息 and 私聊 类型的数据
        user_id = data.get("user_id")           # 后面发包要用， 将 json数据中字段类型为 "user_id"的数据值 --> 变量user_id
        self_id = data.get("self_id")           # 小夕的 qq号

        if self_id == user_id:       # 防死循环：如果发现发消息的人就是机器人自己，说明是 WebSocket 回弹，直接 return 退出！
            return

        message_data = data.get("message",[])   # 接收发来的消息，([]意为)存储消息列表(多个segment)

        logging.info(f"收到 QQ({user_id}) 的消息: {message}")       # 日志信息，不会发到qq

        # 区分消息类型
        message_text = ""
        message_image_url = None
        message_image_desc = ""               # 图片描述
        message_img_failed = False              # 标记：这次发图是不是失败了（网络问题或API挂了）

        # 每条消息分 信息段 处理
        for segment in message_data:
            try:
                segment_type = segment.get("type")        # 从segment中取出 data字典，再从中取出 text类型。如果不存在"data"就返回空字典，如果不存在text就返回空
                
                # 图片信息处理---------------------
                if segment_type == "image":
                    message_image_url = segment.get("data", {}).get("url")          # 获取图片 url
                    logging.info("正在提取图片并转码...")
                    message_image_base64 = url_to_base64(message_image_url)         # 下载图片的 base64

                    if message_image_base64:
                        img_desc = ai_service.qw_describe_img(message_image_base64)
                        if img_desc:
                            message_image_desc += img_desc      # 把图片描述拼起来
                        else:
                            message_img_failed  = True      # API 挂了
                            logging.info(f"识别图片时API挂了")
                    else:
                        message_img_failed = True           # 下载图片就失败了
                        logging.info(f"下载图片失败")

                # 文本信息处理----------------------
                if segment_type == "text":
                    message_text += segment.get("data",{}).get("text","")   # 把文本拼起来
            
            # 异常处理
            except Exception as e:          # Exception是异常基类，里面包含了几乎所有异常情况，异常情况保存到 e 中
                logging.info(f"❌ 处理消息的segment时出现错误: {e}")


        # ==================================================
        # 循环结束：把收集齐的原材料，一次性打包发给记忆模块
        # ==================================================
        # 存入 user 记忆历史
        memory_service.add_user_message_to_history(         # 只是 import，所以需要 . 来找到对应方法
            text=message_text,
            img_desc=message_image_desc,
            img_failed=message_img_failed
        )

        # 呼叫 DeepSeek 思考回复（如果报错，ai_service 内部会返回“网卡了笨蛋”）
        logging.info(" -> 小夕正在组织语言...")
        ai_message = ai_service.ds_general_reply(memory_service.get_history())

        # 存入 assistant 记忆历史
        memory_service.add_ai_message_to_history(ai_message)
        logging.info(f"[小夕说]: {ai_message}")

        # 组装数据包发回 QQ
        reply_pocket = {
                "action": "send_private_msg",        # "action" 是字符串键
                "params": {                          # "params" 是字符串键
                    "user_id": user_id,              # "user_id" 是字符串键，user_id 是变量，上面有
                    "message": ai_message            # "message" 是字符串键，ai_message 是变量，上面有
                }
        }
        ws.send(json.dumps(reply_pocket))       # 将字典 --> json字符串，以便于发送，如果收到表情包类型，则发送空

def on_open(ws):        # 判断启动
    logging.info("🚀 成功连接到 NapCatQQ！小夕在 QQ 守护着你...")        # 打印到日志中


# ==========================================
# 启动入口
# ==========================================
if __name__ == "__main__":
    # 自动清除相同的进程分身
    import pydoc
    import subprocess
    current_pid = os.getpid()       # 获取当前进程的 PID
    current_script = os.path.basename(__file__)     # 获取当前执行的文件名（例如 main.py）
    try:
        # 使用 Linux 的 ps 命令查找所有运行该脚本的 PID
        # awk '{print $2}' 用来提取 PID 这一列
        cmd = f"ps -ef | grep {current_script} | grep -v grep | awk '{{print $2}}'"
        pids = subprocess.check_output(cmd, shell=True).decode().split()            # 执行 shell 命令，捕获输出（字节形式），然后 将字节输出转换为字符串（通常 UTF-8），最后 按空白字符分割，得到 PID 字符串列表
        
        for pid in pids:
            pid = int(pid)
            if pid != current_pid:
                os.kill(pid, 9)
                logging.info(f"🧹 已自动清理历史残留的 Linux 后台进程 (PID: {pid})...")
    except Exception as e:
        # 如果没有找到其他进程，subprocess 会报错，直接忽略即可
        pass

    logging.info("🚀 正在启动持续监听...")

    # 启动持续监听            # WS_URL 设置 WebSocket 连接的地址。127.0.0.1 是本机 IP，3001 是 NapCatQQ 默认开放的端口。如果你的 NapCatQQ 设置的端口不同，需要改这里。
    ws = websocket.WebSocketApp(WS_URL, on_message=on_message, on_open=on_open)     # python中加 = 才能覆盖
    ws.run_forever()    