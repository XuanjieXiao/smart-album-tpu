import requests
import base64
import json
import os

# --- 请在这里配置您的服务信息 ---
# 服务的 IP 地址或域名
API_IP = "172.24.12.226"  # 服务的IP地址
# 服务的端口号
API_PORT = 19091        # 服务的端口
# 要测试的本地图片路径 (支持 jpg, bmp, png)
IMAGE_PATH = "/data/xuanjiexiao/xuanjiexiao/smart-album-tpu/女生.jpg" # 请修改为您的图片路径
# ------------------------------------
def test_face_detection_api(api_url, image_path):
    """
    测试人脸识别API。
    此版本会直接读取图片文件, 在代码中进行Base64编码,
    并保证生成正确的JSON格式。
    
    :param api_url: API的完整URL
    :param image_path: 本地图片的路径
    """
    # 1. 检查图片文件是否存在
    if not os.path.exists(image_path):
        print(f"错误: 图片文件未找到 -> {image_path}")
        return

    # 2. 读取图片文件并进行Base64编码
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            # 这一步会得到一个纯净的Base64字符串
            base64_encoded_data = base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"错误: 读取或编码图片时出错 -> {e}")
        return

    # 3. 准备请求头
    headers = {
        'Content-Type': 'application/json'
    }
    
    # --- 核心保证部分 ---
    # a. 在代码中构建一个标准的Python字典
    payload_dict = {
        "ImageData": base64_encoded_data
    }
    
    # b. 使用 json.dumps() 将字典转换为JSON字符串。
    #    这一步会【强制保证】所有字符串值都使用双引号。
    payload_json_string = json.dumps(payload_dict)
    
    # 您可以在这里打印出来，确认格式绝对正确
    print("--- 调试信息 ---")
    print("代码保证生成的最终JSON字符串:")
    # 为了防止终端打印过多内容，只打印前100个字符
    print(payload_json_string[:100] + "...")
    print("------------------")


    # 4. 发送POST请求
    # 使用 data= 参数来发送我们刚刚在代码中生成的、格式有保证的字符串
    print(f"正在向 {api_url} 发送请求...")
    try:
        response = requests.post(api_url, headers=headers, data=payload_json_string, timeout=20)
        
        # 5. 处理并打印响应
        print("-" * 20 + "  响应结果  " + "-" * 20)
        
        if response.status_code == 200:
            print(f"HTTP状态码: {response.status_code} (成功)")
            response_json = response.json()
            print("收到的JSON数据:")
            print(json.dumps(response_json, indent=4, ensure_ascii=False))
        else:
            print(f"请求失败! HTTP状态码: {response.status_code}")
            print("服务器返回内容:")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"请求时发生严重错误: {e}")
        print("请检查：")
        print(f"1. IP地址 '{API_IP}' 和端口 '{API_PORT}' 是否正确。")
        print("2. 服务是否已成功启动。")
        print("3. 网络连接是否正常，防火墙是否允许访问。")
        
    print("-" * 52)


if __name__ == "__main__":
    # 构建完整的API URL
    url = f"http://{API_IP}:{API_PORT}/image/detection"
    
    # 执行测试
    test_face_detection_api(url, IMAGE_PATH)
