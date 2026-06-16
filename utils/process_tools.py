# 自动清除相同的进程分身
import os
import logging
import subprocess

# 自动清理重复进程
def clear_duplicate_process(main_script_name):
    current_pid = os.getpid()            # 当前文件和主程序处于同一个进程中，共享 PID
    try:
        # 使用 Linux 的 ps 命令查找所有运行该脚本的 PID
        # awk '{print $2}' 用来提取 PID 这一列
        cmd = f"ps -ef | grep {main_script_name} | grep -v grep | awk '{{print $2}}'"
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
