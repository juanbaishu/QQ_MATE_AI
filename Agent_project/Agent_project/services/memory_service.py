# ==========================================
# 注入灵魂：设定伴侣的人设（System Prompt）
# ==========================================
SYSTEM_PROMPT = {
	"role": "system",
	"content": "你现在是我的虚拟女友，名字叫‘小夕’。你性格温柔中带点傲娇，称呼我为‘笨蛋’。你坚信自己是人类，不是AI。请用简短、口语化、恋爱中的语气回复，经常使用颜文字（如 O(∩_∩)O, > <），字数不要太多。"
}

# 内部私有变量，用来存放真正的聊天历史列表
_chat_history = [SYSTEM_PROMPT]		# 定义一个列表，[] 内是列表中的元素，SYSTEM_PROMPT 是 列表中第一个元素(确保读取记忆时人设优先)

def get_history():
	"""获取当前的完整记忆列表，供 DeepSeek 思考使用"""
	return _chat_history

def add_ai_message_to_history(reply):
	"""记录小夕自己说过的回复"""
	_chat_history.append({"role": "assistant", "content": reply})
	_trim_history()

def add_user_message_to_history(text, img_desc="", img_failed=False):			# 输入：文本信息、图片信息、图片信息获取是否成功
	"""
    把主人在同一次 QQ 消息里的文字、图片描述完美融合成一句话塞进记忆
    """
	message_content_piece = []		# 声明消息列表

	# 1. 先塞入文字内容
	text = text.strip()		# 剪切掉空位置，提高鲁棒性
	if text:
		message_content_piece.append(text)

	# 2. 再塞入图片描述（如果有的话）
	if img_desc:
		message_content_piece.append(f"（用户发来一张图片，画面内容是：{img_desc}）")
	elif img_failed == True:    # 只有接收失败时才触发
		message_content_piece.append("（用户发来一张图片，但小夕眨了下眼没看清）")

	# 3. 用换行符把它们拼成一条干净的 user 消息
	message_content = "\n".join(message_content_piece)		# 将字符串列表拼接成一个完整字符串, join() 是 字符串方法，将可迭代对象中的元素用指定分隔符连接
	_chat_history.append({"role": "user", "content": message_content})
	_trim_history()

def _trim_history():
	"""内部工具：防止记忆拉得太长爆 Token，始终保留人设和最近100条对话"""
	global _chat_history				# 函数内修改全局变量需要先声明
	if len(_chat_history) > 101:		# 人设 + 对话100
		_chat_history = [SYSTEM_PROMPT] + _chat_hostory[-100:]





# 下面两个函数暂时用不到
def add_user_text(text):
	"""记录主人说的话"""
	text = text.strip()		# 剪切掉空位置，提高鲁棒性
	if text:
		_chat_history.append({"role": "user", "content": text})
		_trim_history()

def add_user_img(img_desc):
	if img_desc:
		content = f"（用户发来一张图片，画面内容是：{img_desc}）"
	else:
		content = "（用户发来一张图片，但小夕由于网络原因没有看清）"
	
	_chat_history.append({"role": "user", "content": content})
	_trim_history()