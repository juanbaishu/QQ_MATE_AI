# 用于操纵主进程中 websocket 服务的库文件
import json
import logging

_ws_instance = None		# 局部变量

def set_ws(ws):
	"""保存全局 WebSocket 实例"""
	global _ws_instance
	_ws_instance = ws

def send_private_msg(user_id, message):
	"""供任意后台线程调用：主动发送私聊消息"""
	if _ws_instance:
		reply_pocket = {		# {} --> 字典，左边的"action"、"params"、"user_id"、"message"都是字典中的键名
			"action": "send_private_msg",			# onebot协议的格式要求，onebot中规定的api名称为end_private_msg这个字符串，接收这个动作之后就会分析得到发送动作
			"params": {
				"user_id": user_id,				# onebot的内定参数名，和参数名没关系
				"message": message              # 键值对只能用 : 赋值
			}
		}
		_ws_instance.send(json.dumps(reply_pocket))		# 转换成json格式发送
	else:
		logging.error("❌ WebSocket 未初始化，无法主动发送消息！")