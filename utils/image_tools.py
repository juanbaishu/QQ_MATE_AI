import requests         # 用于伪装浏览器去下载图片
import base64           # 图片转译成文本编码 的 工具

# 图像下载工具
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