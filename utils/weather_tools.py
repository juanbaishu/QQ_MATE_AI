import requests         # 已包含 json 解析工具

# 获取天气信息，通过 requests 发送 HTTP 请求，并使用 wttr.in 天气 API
def get_weather(city: str) -> str:		# (参数: 类型) -> 返回类型
    """
    通过调用 wttr.in API 查询真实的天气信息。
    """
	# API端点，我们请求JSON格式的数据
    url = f"https://wttr.in/{city}?format=j1"           # 完全免费的 API 不需要 API KEY，写法在官网手册上有 https://wttr.in/:help，?format=j1 就是告诉服务器："给我JSON格式的数据"。

    try:
        # 发起网络请求
        response = requests.get(url)
        # 检查响应状态码是否为200 (成功)
        response.raise_for_status()             # 自动其中的 response.status_code
        # 解析返回的JSON数据
        data = response.json()                  # 相当于 data = json.load(response.text)

#        # 打印看一下返回的数据结构长什么样
#        print(json.dumps(data, indent=2, ensure_ascii=False))        # 打印 data，换行并缩进，正常打印非ascii的中文          dumps表示字符串

        # 提取当前天气状况
        # ↓字典                       ↓列表
        current_condition = data['current_condition'][0]                # ['current_condition']是 关键字，从 data 字典中取出一个列表，左边的是任意变量，[0]是从current_condition列表中取出 第一个(元素) {} 中的内容
        weather_desc = current_condition['weatherDesc'][0]['value']    # 只要是 列表，都需要后加 [] 来选择
        temp_c = current_condition['temp_C']

        # 格式化成自然语言返回
        return f"{city}当前天气：{weather_desc}，气温：{temp_c}摄氏度"



    except requests.exceptions.RequestException as e:
        # 处理网络错误
        print(f"错误：查询天气时发生网络异常，{e}")        # f 能让字符串 e 替换

    except (KeyError, IndexError) as e:
        # 处理数据解析错误
        print(f"错误：解析天气数据失效，可能是城市名无效，{e}")
        
if __name__ == "__main__":
    # 测试一下
    print(get_weather("Beijing"))
    print(get_weather("Shanghai"))