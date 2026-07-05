# 主程序控制中心
import os			                # 将 Python 标准库中的 os 模块引入到当前程序中
import json			                # JavaScript 格式，最通用的文本格式
import websocket	                # 连接 Python 和 NapCatqq 的 网络通信协议     
import logging                      # 引入 python 官方的 logging 库，以便在代码里打日志

# 从拆分出来的文档中，导入需要的工具
from config import WS_URL
#from ai_service import qw_describe_img, ds_general_reply		# 定义的两个方法
from services import ai_service
from services import memory_service
from services import ws_service                 # 控制websocket的库，用于主动发消息
from utils.image_tools import url_to_base64
from utils import logs_tools                    # 日志的配置文件，会自动执行
from utils import process_tools


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

        logging.info(f"收到 QQ({user_id}) 的消息: ...")       # 日志信息，不会发到qq

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
        ai_message = ai_service.ds_general_reply(user_id, memory_service.get_history())

        # 存入 assistant 记忆历史
        memory_service.add_ai_message_to_history(ai_message)
        logging.info(f"[小夕说]: {ai_message}")

        # 组装数据包发回 QQ
        reply_pocket = {            # 基于onebot协议的架构
                "action": "send_private_msg",        # "action" 是键名，"send_private_msg"是onebot协议中的api名称
                "params": {                          # "params" 是键名
                    "user_id": user_id,              # "user_id" 是键名，user_id 是变量，上面有
                    "message": ai_message            # "message" 是键名，ai_message 是变量，上面有
                }
        }
        ws.send(json.dumps(reply_pocket))       # 将字典 --> json字符串，以便于发送，如果收到表情包类型，则发送空

def on_open(ws):        # 判断启动
    ws_service.set_ws(ws)     # 缓存 websocket 实例供后台使用
    logging.info("🚀 成功连接到 NapCatQQ！小夕在 QQ 守护着你...")        # 打印到日志中


# ==========================================
# 启动入口
# ==========================================
if __name__ == "__main__":
    # 自动清理重复进程
    process_tools.clear_duplicate_process("QQ_MATE_AI.py")

    # 启动持续监听            # WS_URL 设置 WebSocket 连接的地址。127.0.0.1 是本机 IP，3001 是 NapCatQQ 默认开放的端口。如果你的 NapCatQQ 设置的端口不同，需要改这里。
    ws = websocket.WebSocketApp(WS_URL, on_message=on_message, on_open=on_open)     # python中加 = 才能覆盖
    ws.run_forever()    