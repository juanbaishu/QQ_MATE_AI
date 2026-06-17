import logging
# ==========================================
# 日志系统配置
# ==========================================
logging.basicConfig(
    level=logging.INFO,  # 记录的最低级别，INFO及以上的都会被记录
    format='%(asctime)s [%(levelname)s] %(message)s',  # 日志格式：时间 [级别] 消息内容
    datefmt='%Y-%m-%d %H:%M:%S',  # 时间格式
    handlers=[
        logging.FileHandler("../logs/ai_bot.log", encoding="utf-8", mode='a'),  # 1. 写入到文件 (a表示追加模式)
        logging.StreamHandler()  # 2. 同时输出到黑色控制台
    ]
)