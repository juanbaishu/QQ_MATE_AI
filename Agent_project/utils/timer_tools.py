# 用于实现 倒计时 和 绝对时间 两个时间功能，涉及多线程操作
# 这里实现的是 多线程 和 异步回调，所以每个任务都是隔离的，不会变量混淆
import logging
from datetime import datetime, timedelta        # python自带时间库
from apscheduler.schedulers.background import BackgroundScheduler       # 线程定时任务服务
from services import ws_service
from services import memory_service

# 引入ai判断取消闹钟的逻辑
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
ai_matcher_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)        # 初始化ai客户端

def is_match_by_ai(keyword: str, alarm_msg: str) -> bool:
    """
    内部小工具：让大模型判断用户的关键词是否和闹钟内容匹配
    """
    prompt = (
        f"你是一个严格的逻辑判断器。请判断用户想取消的【关键词】是否在语义上指代了【闹钟内容】。\n"
        f"比如：关键词是'锻炼'或'腿部'，闹钟内容是'去做深蹲和拉伸'，则匹配成功。\n\n"
        f"【关键词】：{keyword}\n"
        f"【闹钟内容】：{alarm_msg}\n\n"
        f"如果匹配请只回复 True，如果不匹配请只回复 False，不要输出任何其他标点或解释。"
    )

    try:
        # 调用ai判断 keyword 和 alarm_msg 是否匹配
        response = ai_matcher_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0  # 温度设为0，保证输出绝对稳定
        )
        ai_result = response.choices[0].message.content.strip().lower()     # .strip() --> 去除首尾空白字符     .lower() --> 转换成小写

        if 'true' in ai_result:
            return True
        else:
            return False

    except Exception as e:
        logging.error(f"⚠️ AI 匹配闹钟语义时报错: {e}，将降级使用基础字面匹配。")
        # 降级方案：如果网络波动导致大模型掉线，退回原始的包含判断，保证程序不崩
        return keyword in alarm_msg


# 初始化并启动后台调度器
scheduler = BackgroundScheduler()       # 创建了一个"定时任务管理器"，并让它开始在后台运行。
scheduler.start()

def timer_callback(user_id, message):       # 发送信息，并存入ai视角的记忆中
    """时间到了，实际触发的回调函数"""
    logging.info(f"⏰ 定时任务触发，正在主动发送给 QQ({user_id}): {message}")
    ws_service.send_private_msg(user_id, message)
    memory_service.add_ai_message_to_history(f"（主动提醒用户）：{message}")


def set_timer(user_id: int, delay_minutes: int, message: str) -> str:
    """工具1：设置倒计时（相对时间），一次性闹钟"""
    if not user_id:
        return "错误：缺少用户 ID。"

    target_time = datetime.now() + timedelta(minutes=delay_minutes)     # minutes是关键字，用它的自动转换来确定单位。        得到执行的时间点
    scheduler.add_job(func=timer_callback, trigger='date', run_date=target_time, args=[user_id, message])       # 增加调度器任务，参数：1.执行的函数  2.循环执行次数器,'date'对应一次  3.执行时间  4.传入参数
    
    time_str = target_time.strftime('%Y-%m-%d %H:%M:%S')        # target_time 接收完上面的时间对象的结果后，结构发生了变化，变成了时间对象，因此能够调用.strftime()方法
    return f"已成功设置倒计时！将于 {delay_minutes} 分钟后（{time_str}）提醒主人：{message}"


def set_alarm(user_id: int, target_time: str, message: str) -> str:
    """工具2：设置定点闹钟（绝对时间），一次性闹钟"""
    if not user_id:
        return "错误：缺少用户 ID。"

    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%H:%M:%S", "%H:%M"]      # 这是"解析模板"列表，告诉程序用户可能输入的时间格式
    parsed_time = None      # 得到的符合格式的时间

    for fmt in formats:     # 依次尝试每种格式
        try:
            parsed_time = datetime.strptime(target_time, fmt)       # target_time --转化--> fmt格式，如果格式不匹配，会自动抛出ValueError的异常
            # 用户没有说日期，需要自动化判断
            if fmt in ["%H:%M:%S", "%H:%M"]:
                now = datetime.now()
                parsed_time = parsed_time.replace(year=now.year, month=now.month, day=now.day)
                if parsed_time < now:
                    parsed_time += timedelta(days=1)
            break       # 成功后退出
        except ValueError:
            continue

    if not parsed_time:
        return f"错误：时间格式无法解析，收到的字符串为: {target_time}"

    scheduler.add_job(func=timer_callback, trigger='date', run_date=parsed_time, args=[user_id, message])
    time_str = parsed_time.strftime('%Y-%m-%d %H:%M:%S')
    return f"已成功设置定点闹钟！小夕将于 {time_str} 准时提醒主人：{message}"
    

def set_daily_alarm(user_id: int, time_str: str, message: str) -> str:
    """
    工具3：设置每天定期的循环闹钟
    参数 time_str 格式必须为 'HH:MM'，例如 '08:00'
    """
    if not user_id:
        return "错误：缺少用户 ID。"

    try:
        # 解析出对应的时刻：hour、minute
        time_obj = datetime.strptime(time_str, '%H:%M')     # 必须用 datetime 调用，且格式化占位符需要带 % 号
        hour = time_obj.hour
        minute = time_obj.minute
    except ValueError:
        return f"错误：时间格式无法解析，请使用 HH:MM 格式，当前收到: {time_str}"

    # 这里使用的是 'cron' 触发器，它会自动处理每天的循环 apscheduler库中基于python实现的定时任务工具
    scheduler.add_job(
        func=timer_callback,
        trigger='cron',
        hour=hour,
        minute=minute,
        args=[user_id, message]
    )

    return f"已成功设置每日闹钟！小夕将在每天的 {time_str} 准时提醒主人：{message}"


def cancel_specific_alarm(user_id: int, keyword: str, message: str) -> str:         # message就是取消任务后，ai对应的日志回复
    """工具4：根据关键词，定点取消指定的闹钟任务"""
    if not user_id:
        return "错误：缺少用户 ID。"
    if not keyword:
        return "错误：缺少需要匹配的关键词。"

    delete_count = 0

    # 获取后台运行的所有定时任务
    for job in scheduler.get_jobs():
        # 核对是不是该用户的任务，并且提取出当初存进去的提醒内容 message
        if job.args and job.args[0] == user_id:
            alarm_msg = job.args[1]

            # AI 语义判断需要取消的任务
            if is_match_by_ai(keyword, alarm_msg):
                scheduler.remove_job(job.id)
                delete_count += 1

    if delete_count == 0:
        return f"取消失败：小夕在后台找了一圈，没发现符合“{keyword}”意图的闹钟哦。"

    return f"精准取消成功！已删除了 {delete_count} 个相关的提醒。小夕：{message}"