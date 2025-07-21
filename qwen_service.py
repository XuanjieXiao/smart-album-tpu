from openai import OpenAI
import base64
import os
import logging
import json
import re # 引入正则表达式库
from PIL import Image # 用于图片处理
import io # 用于内存中的字节流操作
# import html # For unescaping HTML entities if necessary

# 配置日志格式和等级
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler("analyze_images.log", encoding='utf-8')
    ]
)

# --- 全局变量 ---
client = None
QWEN_MODEL_NAME = "Qwen2.5-VL-7B-Instruct" # 默认模型名称
model_flag = ""

def init_qwen_client(api_key: str, base_url: str, model_name: str):
    """
    使用新的配置初始化或重新初始化Qwen-VL OpenAI客户端。
    """
    global client, QWEN_MODEL_NAME, model_flag

    if api_key == "null":
        model_flag = "local_model"
    else:
        model_flag = "online_model"

    if not api_key or not base_url or not model_name:
        client = None
        # 如果传入的model_name为空，则保留默认值
        QWEN_MODEL_NAME = model_name or "Qwen2.5-VL-7B-Instruct"
        logging.warning("由于缺少 API Key、Base URL 或模型名称，Qwen-VL 客户端未初始化。")
        return

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        QWEN_MODEL_NAME = model_name
        logging.info(f"Qwen-VL 服务已初始化。模型: '{QWEN_MODEL_NAME}', Base URL: '{base_url}'")
    except Exception as e:
        client = None
        logging.error(f"初始化 Qwen-VL OpenAI 客户端失败: {e}")


MAX_BASE64_IMAGE_CHARS = 7 * 1024 * 1024

def _prepare_image_data_for_qwen(image_path: str, max_chars: int = MAX_BASE64_IMAGE_CHARS) -> str | None:
    try:
        img = Image.open(image_path)
    except FileNotFoundError:
        logging.error(f"图片文件未找到: {image_path}")
        return None
    except Exception as e:
        logging.error(f"使用Pillow打开图片失败 '{image_path}': {e}")
        return None

    if img.mode not in ('RGB', 'L'):
        try:
            img = img.convert('RGB')
        except Exception as e:
            logging.error(f"图片 '{image_path}' 转换为RGB模式失败: {e}")
            return None

    current_quality = 90
    max_resize_attempts = 5
    min_dimension = 100
    original_dims = img.size

    for attempt in range(max_resize_attempts):
        buffer = io.BytesIO()
        try:
            img.save(buffer, format="JPEG", quality=current_quality)
        except Exception as e:
            logging.error(f"保存图片到内存缓冲区失败 (尝试 {attempt + 1}) for '{image_path}': {e}")
            return None

        base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        current_base64_size_mb = len(base64_str) / (1024 * 1024)

        if len(base64_str) <= max_chars:
            logging.info(f"图片 '{image_path}' (原始尺寸: {original_dims}, 当前尺寸: {img.size}, 质量: {current_quality}, 尝试 {attempt + 1}) "
                         f"成功编码为Base64，大小: {current_base64_size_mb:.2f} MB。")
            return f"data:image/jpeg;base64,{base64_str}"

        logging.info(f"图片 '{image_path}' Base64大小 ({current_base64_size_mb:.2f} MB) 超过限制. 尝试缩减...")
        if attempt < max_resize_attempts - 1:
            new_width = int(img.width * 0.8)
            new_height = int(img.height * 0.8)
            if new_width < min_dimension or new_height < min_dimension:
                logging.warning(f"图片 '{image_path}' 尺寸已过小 ({new_width}x{new_height})，停止缩减。")
                break
            try:
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            except Exception as e:
                logging.error(f"图片缩放失败 (尝试 {attempt + 1}) for '{image_path}': {e}")
                break
            if current_quality > 65: current_quality -= 5
        else:
            logging.warning(f"图片 '{image_path}' 达到最大缩减尝试次数，但仍超过大小限制。")
    logging.error(f"图片 '{image_path}' 无法在 {max_resize_attempts} 次尝试内缩减到符合API大小限制。")
    return None

def strip_html(text: str) -> str:
    """移除文本中的HTML标签。"""
    if not text or not isinstance(text, str):
        return ""
    clean = re.compile('<.*?>')
    text_no_html = re.sub(clean, '', text)
    # text_no_html = html.unescape(text_no_html)
    return text_no_html.strip()

def clean_and_format_keywords(raw_keywords) -> list:
    """
    清理和格式化从API获取的关键词。
    raw_keywords 可以是列表或单个字符串。
    """
    cleaned_keywords_intermediate = []
    
    items_to_process = []
    if isinstance(raw_keywords, list):
        items_to_process = raw_keywords
    elif isinstance(raw_keywords, str):
        if raw_keywords.startswith('[') and raw_keywords.endswith(']'):
            try:
                potential_list = json.loads(raw_keywords)
                if isinstance(potential_list, list):
                    items_to_process = potential_list
                else:
                    items_to_process = [raw_keywords]
            except json.JSONDecodeError:
                items_to_process = [raw_keywords]
        else:
            items_to_process = [raw_keywords]

    for item in items_to_process:
        if isinstance(item, str):
            temp_kw_str = item.strip()
            
            while len(temp_kw_str) >= 2 and \
                  ((temp_kw_str.startswith('"') and temp_kw_str.endswith('"')) or \
                   (temp_kw_str.startswith("'") and temp_kw_str.endswith("'"))):
                temp_kw_str = temp_kw_str[1:-1].strip()

            split_kws = re.split(r'[,\s、]+', temp_kw_str)
            for kw_part in split_kws:
                kw_final = kw_part.strip()
                if kw_final:
                    cleaned_keywords_intermediate.append(kw_final)

    final_keywords_unique = []
    for kw in cleaned_keywords_intermediate:
        if kw and kw not in final_keywords_unique:
            final_keywords_unique.append(kw)
    return final_keywords_unique[:10]


def analyze_image_content(image_path: str):
    """
    分析单张图片的内容，根据model_flag（local_model或online_model）采用不同策略。
    - local_model: 进行一次API调用，直接返回文本描述。
    - online_model: 进行带重试和复杂解析的API调用，期望获得JSON格式的结果。
    """
    if not client:
        logging.error("Qwen-VL 客户端未初始化。无法分析图片。请在控制面板中配置API Key, Base URL和模型名称。")
        return {"description": "Qwen服务未配置", "keywords": []}

    logging.info(f"准备分析图片: {image_path} (模型类型: {model_flag})")
    data_url = _prepare_image_data_for_qwen(image_path)
    if not data_url:
        return {"description": "", "keywords": []}

    # --- 修改核心：根据 model_flag 分支处理 ---

    # 分支1：本地模型 - 简单、直接的单次调用
    if model_flag == "local_model":
        prompt_text = "用中文详细描述这张图，必须描述完图片里面的所有元素以及物品信息，重点描述元素的颜色、人物的穿着、车辆信息、物品信息，总字数不要超过450。"
        logging.info(f"开始本地模型图片分析 for image: {image_path}")
        try:
            response = client.chat.completions.create(
                model=QWEN_MODEL_NAME,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]}
                ],
                stream=False
            )
            # 直接获取内容，不进行JSON解析
            # 注意：这里的响应结构是基于原代码的假设，如果您的本地模型响应不同，请调整此处
            description = response.choices[0].message[0].content.strip()
            logging.info(f"本地模型分析成功: {image_path}")
            return {"description": description, "keywords": []}
        except Exception as e:
            logging.error(f"本地模型Qwen-VL分析图片API调用失败: {e}", exc_info=True)
            return {"description": f"本地模型API调用失败: {e}", "keywords": []}

    # 分支2：在线模型 - 复杂的、带重试和JSON解析的调用
    elif model_flag == "online_model":
        prompt_text = """请你严格作为图片分析JSON生成器运行。你的唯一输出必须是一个符合下述规范的JSON对象。

图片分析要求：
1.  **描述 (description)**: 用中文详细描述图片内容、物品、元素和场景。描述应简洁明了。此描述文本中绝对不允许包含任何HTML标签 (如 `<p>`, `<b>` 等)。如果描述中需要使用英文双引号 (`"`)，则必须将其转义为 `\\"`.
2.  **关键词 (keywords)**: 从图片内容中提取最多10个最具代表性的中文关键词。此字段必须是一个JSON数组，其中每个元素都是一个独立的、纯净的中文关键词字符串。例如：`["天空", "建筑", "城市"]`。单个关键词字符串内部不应包含任何引号、逗号或其他分隔符。

JSON输出格式 (严格遵守，不要添加任何额外字符、注释或Markdown标记如 ```json):
{
  "description": "图片描述文本。",
  "keywords": ["关键词示例1", "关键词示例2"]
}

字数限制：整个JSON响应（包括JSON结构本身和所有文本内容）的总字数不要超过490字。"""
        
        MAX_API_ATTEMPTS = 3
        last_successful_api_content_if_unparsed = None
        last_api_call_exception_details = None

        for attempt_num in range(MAX_API_ATTEMPTS):
            current_attempt_str = f"Attempt {attempt_num + 1}/{MAX_API_ATTEMPTS}"
            logging.info(f"开始在线模型图片分析 - {current_attempt_str} for image: {image_path}")
            try:
                response = client.chat.completions.create(
                    model=QWEN_MODEL_NAME,
                    messages=[
                        {"role": "user", "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": data_url}}
                        ]}
                    ],
                    stream=False
                )
                result_content = response.choices[0].message.content.strip()
                last_successful_api_content_if_unparsed = result_content
                last_api_call_exception_details = None
                logging.info(f"在线模型API调用成功: {image_path} ({current_attempt_str})")
                logging.debug(f"Qwen-VL原始输出 ({current_attempt_str}): '{result_content}'")

                json_str_candidate = None
                match_md = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', result_content, re.DOTALL)
                if match_md:
                    json_str_candidate = match_md.group(1).strip()
                    logging.info(f"从Markdown JSON块提取候选JSON ({current_attempt_str}).")
                else:
                    match_curly = re.search(r'(\{[\s\S]*\})', result_content, re.DOTALL)
                    if match_curly:
                        json_str_candidate = match_curly.group(1).strip()
                        logging.info(f"从裸JSON对象结构提取候选JSON ({current_attempt_str}).")
                    else:
                        logging.warning(f"在API响应中未找到可识别的JSON结构 ({current_attempt_str}).")
                
                if json_str_candidate:
                    try:
                        json_str_candidate = json_str_candidate.replace('\u00a0', ' ')
                        parsed_data = json.loads(json_str_candidate)
                        
                        description_raw = parsed_data.get("description", "")
                        description = strip_html(description_raw) if isinstance(description_raw, str) else ""

                        keywords_raw = parsed_data.get("keywords", [])
                        keywords = clean_and_format_keywords(keywords_raw)

                        logging.info(f"JSON成功解析和清理 ({current_attempt_str}).")
                        return {"description": description, "keywords": keywords}

                    except json.JSONDecodeError as je:
                        logging.warning(f"JSON解析失败 ({current_attempt_str}). Error: {je}")
                
                if attempt_num < MAX_API_ATTEMPTS - 1:
                    logging.info(f"当前尝试解析失败，将进行下一次API调用 ({attempt_num + 2}/{MAX_API_ATTEMPTS}).")

            except Exception as e:
                logging.error(f"在线模型Qwen-VL分析图片API调用失败 ({current_attempt_str}): {e}", exc_info=True)
                last_api_call_exception_details = str(e)
                if attempt_num < MAX_API_ATTEMPTS - 1:
                    logging.info(f"由于API调用错误，将进行下一次尝试 ({attempt_num + 2}/{MAX_API_ATTEMPTS}).")
        
        # Fallback after all API attempts for online model
        logging.error(f"所有 {MAX_API_ATTEMPTS} 次在线模型API尝试均已完成，但未能成功解析出有效JSON。")
        if last_successful_api_content_if_unparsed:
            logging.warning("将最后一次成功的API原始响应作为描述返回（无关键词）。")
            return {"description": strip_html(last_successful_api_content_if_unparsed), "keywords": []}
        elif last_api_call_exception_details:
            logging.error(f"所有API调用均失败。最后记录的API错误: {last_api_call_exception_details}")
            return {"description": f"API调用在所有{MAX_API_ATTEMPTS}次尝试后均失败: {last_api_call_exception_details}", "keywords": []}
        else:
            logging.error("所有尝试后均无有效内容或错误记录。返回通用失败信息。")
            return {"description": "图片分析失败，请稍后重试。", "keywords": []}

    # 分支3：未知的模型标志
    else:
        logging.error(f"未知的 model_flag: '{model_flag}'。无法确定分析策略。")
        return {"description": f"模型标志 '{model_flag}' 配置错误，请检查。", "keywords": []}