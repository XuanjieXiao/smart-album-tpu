# face_service.py
import requests
import base64
import logging
import os
import numpy as np

# 全局客户端配置
face_api_client = {
    "base_url": "http://127.0.0.1:8000", # 请根据实际情况修改IP和端口
    "headers": {"Content-Type": "application/json"}
}

def init_face_client(base_url: str):
    """
    初始化人脸识别服务的API客户端配置。
    """
    if base_url:
        face_api_client["base_url"] = base_url
        logging.info(f"人脸识别服务 URL 已更新为: {base_url}")

def detect_faces(image_path: str):
    """
    调用外部API，对指定图片进行人脸检测和特征提取。

    Args:
        image_path (str): 本地图片文件的绝对路径。

    Returns:
        list | None: 包含检测到的人脸信息的列表，或在失败时返回None。
                      每个元素是一个字典，包含 'FaceBox', 'FeatureData' (numpy array), 'FacialAttributes', 'Score'。
    """
    if not os.path.exists(image_path):
        logging.error(f"[Face Service] 图片文件不存在: {image_path}")
        return None

    # 检查文件大小和格式
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
    if file_size_mb > 3:
        logging.warning(f"[Face Service] 图片 {os.path.basename(image_path)} 大小超过3MB，跳过人脸识别。")
        return None
        
    file_ext = os.path.splitext(image_path)[1].lower()
    if file_ext not in ['.jpg', '.jpeg', '.png', '.bmp']:
        logging.warning(f"[Face Service] 图片 {os.path.basename(image_path)} 格式不受支持 ({file_ext})，跳过人脸识别。")
        return None

    api_url = f"{face_api_client['base_url']}/image/detection"
    
    try:
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')

        payload = {"ImageData": image_base64}
        response = requests.post(api_url, json=payload, headers=face_api_client['headers'], timeout=30)
        response.raise_for_status() # 抛出HTTP错误

        data = response.json()

        if data.get("Code") == 0 and "Result" in data:
            logging.info(f"[Face Service] 成功检测到 {len(data['Result'])} 张人脸于图片 {os.path.basename(image_path)}。")
            processed_results = []
            for face_res in data["Result"]:
                # 将Base64编码的特征解码为Numpy数组
                feature_bytes = base64.b64decode(face_res["FeatureData"])
                # 特征是float32类型。一个float32占4个字节。
                face_feature_vector = np.frombuffer(feature_bytes, dtype=np.float32)
                face_res["FeatureData"] = face_feature_vector
                processed_results.append(face_res)
            return processed_results
        else:
            logging.error(f"[Face Service] API返回错误: Code={data.get('Code')}, Msg={data.get('Msg')}")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"[Face Service] 调用人脸识别API失败: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"[Face Service] 处理人脸识别响应时发生未知错误: {e}", exc_info=True)
        return None