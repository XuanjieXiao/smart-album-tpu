# AlbumForSearch/app.py
import os
import sys
import logging
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import numpy as np
from PIL import Image
import uuid
from datetime import datetime
import tempfile # Added for temporary file handling
import argparse
import cv2
import sys
import threading
import time

def get_base_path():
    """
    获取资源的基准路径，完美兼容开发模式、--onedir模式和--onefile模式。
    """
    if getattr(sys, 'frozen', False):
        # 如果是PyInstaller打包后的可执行文件
        # sys.executable 指向可执行文件本身
        # 对于 --onedir, 我们要的是可执行文件所在的目录
        # 对于 --onefile, 我们要把模型放在可执行文件旁边，所以还是用它所在的目录
        return os.path.dirname(sys.executable)
    else:
        # 如果是正常的.py脚本运行
        return os.path.dirname(os.path.abspath(__file__))

    
BASE_DIR = get_base_path()
logging.info(f"Application base path determined as: {BASE_DIR}")

logging.info("welcome using sophgo smart album!")

# --- 项目路径配置 ---
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_DIR = BASE_DIR

# --- 服务导入 ---
try:
    import clip
    logging.info("Chinese_CLIP 包导入成功。")
except ImportError as e:
    logging.error(f"导入 依赖包失败: {e}. 请确保 {e}已经安装好。")
    sys.exit(1)

import bce_embedding
import qwen_service
import database_utils as db
import faiss_utils as fu

# --- 新增/修改开始 ---
# 导入新增的人脸服务模块
import face_service
import faiss_face_utils as ffu_face # 使用别名以区分
# --- 新增/修改结束 ---


# --- Flask 应用初始化 ---
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app) # Allow all origins by default

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

# --- 全局配置和常量 ---
CLIP_MODEL_NAME = "ViT-H-14" 
CLIP_MODEL_DOWNLOAD_ROOT = os.path.join(CURRENT_DIR, "models")

UPLOADS_DIR = os.path.join(CURRENT_DIR, "uploads")
THUMBNAILS_DIR = os.path.join(CURRENT_DIR, "thumbnails")
TEMP_SEARCH_UPLOADS_DIR = os.path.join(UPLOADS_DIR, "temp_search") # For temporary search images
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)
os.makedirs(TEMP_SEARCH_UPLOADS_DIR, exist_ok=True) # Create temp dir for search image
os.makedirs(os.path.join(CURRENT_DIR, "data"), exist_ok=True) 
os.makedirs(CLIP_MODEL_DOWNLOAD_ROOT, exist_ok=True)

clip_model = None
clip_preprocess = None

# --- 批量增强分析状态管理 ---
batch_enhance_status = {
    "is_running": False,
    "is_stopped": False,
    "total_images": 0,
    "processed_count": 0,
    "current_image_id": None,
    "current_image_filename": None,
    "start_time": None,
    "errors": [],
    "last_error": None
}
batch_enhance_thread = None
batch_enhance_lock = threading.Lock()


# --- 应用配置 (可持久化或从配置文件加载) ---
APP_CONFIG_FILE = os.path.join(CURRENT_DIR, "data", "app_config.json")

# --- 新增/修改开始 ---
# 在默认配置中加入人脸相关设置
default_app_config = {
    "qwen_vl_analysis_enabled": True,
    "use_enhanced_search": True,
    "qwen_model_name": "Qwen2.5-VL-7B-Instruct",
    "qwen_api_key": "YOUR_QWEN_API_KEY", # 请替换为您的有效Key
    "qwen_base_url": "https://www.sophnet.com/api/open-apis/v1",
    # 人脸识别相关配置
    "face_recognition_enabled": True, # 是否在上传时自动识别人脸
    "face_api_url": "http://127.0.0.1:8000", # 您的人脸识别服务地址
    "face_cluster_threshold": 0.5, # 人脸聚类相似度阈值 (内积)，需要根据模型效果微调
}
# --- 新增/修改结束 ---

app_config = {}

def load_app_config():
    global app_config
    if os.path.exists(APP_CONFIG_FILE):
        try:
            with open(APP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                app_config = json.load(f)
            # 确保所有默认键都存在
            for key, value in default_app_config.items():
                app_config.setdefault(key, value) 
            logging.info(f"应用配置已从 {APP_CONFIG_FILE} 加载。")
        except Exception as e:
            logging.error(f"从 {APP_CONFIG_FILE} 加载配置失败: {e}。使用默认配置。")
            app_config = default_app_config.copy()
    else:
        logging.info("未找到应用配置文件。使用默认配置并创建新文件。")
        app_config = default_app_config.copy()
        save_app_config()

def save_app_config():
    global app_config
    try:
        os.makedirs(os.path.dirname(APP_CONFIG_FILE), exist_ok=True)
        with open(APP_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(app_config, f, indent=4, ensure_ascii=False)
        logging.info(f"应用配置已保存到 {APP_CONFIG_FILE}。")
    except Exception as e:
        logging.error(f"保存配置到 {APP_CONFIG_FILE} 失败: {e}")


def load_bce_model_on_startup(args):
    global bce_service
    try:
        logging.info(f"正在加载 BCE 模型: {args.bce_model} (设备: {args.dev_id})")
        bce_service = bce_embedding.load(args.bce_model, args.dev_id)
        logging.info("BCE 模型加载成功。")
    except Exception as e:
        logging.error(f"加载 BCE 模型失败: {e}", exc_info=True)
        bce_service = None

def load_clip_model_on_startup(args):
    global clip_model, clip_preprocess
    try:
        logging.info(f"正在加载 Chinese-CLIP 模型: {args.image_model} (设备: {args.dev_id})")
        clip_model, clip_preprocess = clip.load(args.image_model, args.text_model, args.dev_id)
        
        dummy_np = np.zeros((224, 224, 3), dtype=np.uint8)  # BGR format, 0值为黑图
        dummy_tensor = np.expand_dims(clip_preprocess(dummy_np), axis=0)
        dummy_feat = clip_model.encode_image(dummy_tensor)
        actual_clip_dim = dummy_feat.shape[1]
        
        if actual_clip_dim != fu.CLIP_EMBEDDING_DIM:
            logging.error(f"致命错误: CLIP模型 '{CLIP_MODEL_NAME}' 的实际输出维度 ({actual_clip_dim}) "
                          f"与 faiss_utils.py 中配置的 CLIP_EMBEDDING_DIM ({fu.CLIP_EMBEDDING_DIM}) 不符。请修正配置。")
        else:
            logging.info(f"Chinese-CLIP 模型 '{CLIP_MODEL_NAME}' 加载成功。图像特征维度: {actual_clip_dim} (与配置一致)")

    except Exception as e:
        logging.error(f"加载 Chinese-CLIP 模型失败: {e}", exc_info=True)
        clip_model = None

def compute_clip_image_embedding(image_path: str) -> np.ndarray | None:
    if not clip_model or not clip_preprocess:
        logging.error("CLIP模型未加载，无法计算图像 embedding。")
        return None
    try:
        img = cv2.imread(image_path)
        image_input = np.expand_dims(clip_preprocess(img), axis=0)
        image_features = clip_model.encode_image(image_input)
        image_features /= np.linalg.norm(image_features,axis=-1, keepdims=True)
        return image_features.astype(np.float32)[0]
    except Exception as e:
        logging.error(f"计算图像 '{image_path}' 的CLIP embedding失败: {e}")
        return None

def compute_clip_text_embedding(text: str) -> np.ndarray | None:
    if not clip_model:
        logging.error("CLIP模型未加载，无法计算文本 embedding。")
        return None
    try:
        tokens = clip.tokenize([text])
        text_features = clip_model.encode_text(tokens)
        text_features /= np.linalg.norm(text_features,axis=-1, keepdims=True)
        return text_features.astype(np.float32)[0]
    except Exception as e:
        logging.error(f"计算文本 '{text[:20]}...' 的CLIP embedding失败: {e}")
        return None

def generate_thumbnail(image_path: str, thumbnail_path: str, size=(256, 256)):
    try:
        img = Image.open(image_path)
        img.thumbnail(size)
        if img.mode == 'RGBA' or img.mode == 'LA' or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGB')
        img.save(thumbnail_path)
        return True
    except Exception as e:
        logging.error(f"生成缩略图失败 for {image_path}: {e}")
        return False

def process_single_image_upload(file_storage):
    original_filename = file_storage.filename
    logging.info(f"[process_single_image_upload] 开始处理文件: {original_filename}")
    
    file_extension = os.path.splitext(original_filename)[1].lower()
    if not file_extension or file_extension not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        logging.warning(f"不支持的文件扩展名: {file_extension} for file {original_filename}. 跳过。")
        return None

    unique_filename_base = str(uuid.uuid4())
    saved_original_filename = unique_filename_base + file_extension
    # Absolute path for file operations
    original_path_abs = os.path.join(UPLOADS_DIR, saved_original_filename)
    
    saved_thumbnail_filename = unique_filename_base + "_thumb.jpg" 
    # Absolute path for file operations
    thumbnail_path_abs = os.path.join(THUMBNAILS_DIR, saved_thumbnail_filename)

    # Relative paths for database storage
    relative_original_path = os.path.join("uploads", saved_original_filename)
    relative_thumbnail_path = None
    
    image_db_id = None
    actual_faiss_id = None 

    try:
        file_storage.save(original_path_abs)
        logging.info(f"图片 '{original_filename}' 已保存到 '{original_path_abs}'")

        if generate_thumbnail(original_path_abs, thumbnail_path_abs):
            relative_thumbnail_path = os.path.join("thumbnails", saved_thumbnail_filename)
        else:
            thumbnail_path_abs = None 

        clip_img_emb = compute_clip_image_embedding(original_path_abs)
        if clip_img_emb is None:
            logging.error(f"无法为图片 '{original_filename}' 生成CLIP embedding。跳过此图片。")
            if os.path.exists(original_path_abs): os.remove(original_path_abs)
            if thumbnail_path_abs and os.path.exists(thumbnail_path_abs): os.remove(thumbnail_path_abs)
            return None

        zeros_bce_emb = np.zeros(fu.BCE_EMBEDDING_DIM, dtype=np.float32)
        concatenated_emb = np.concatenate((clip_img_emb, zeros_bce_emb))
        
        # --- MODIFIED: Store relative paths in DB ---
        image_db_id = db.add_image_to_db(
            original_filename=original_filename,
            original_path=relative_original_path, 
            thumbnail_path=relative_thumbnail_path, 
            clip_embedding=clip_img_emb 
        )

        if image_db_id:
            actual_faiss_id = image_db_id 
            db.update_faiss_id_for_image(image_db_id, actual_faiss_id) 

            if fu.add_vector_to_index(concatenated_emb, actual_faiss_id):
                logging.info(f"图片 '{original_filename}' (DB ID: {image_db_id}, FAISS ID: {actual_faiss_id}) 处理完成并入库。")
                
                if app_config.get("qwen_vl_analysis_enabled", True):
                    logging.info(f"全局Qwen-VL分析已开启，开始分析图片 ID: {image_db_id} (文件名: {original_filename})")
                    qwen_result = qwen_service.analyze_image_content(original_path_abs) # Use absolute path for analysis
                    
                    # 检查分析是否成功
                    if qwen_result and qwen_result.get("success") and (qwen_result.get("description") or qwen_result.get("keywords")):
                        db.update_image_enhancement(image_db_id, qwen_result["description"], qwen_result["keywords"])
                        
                        bce_desc_emb = bce_service.get_bce_embedding(qwen_result["description"]) 
                        if bce_desc_emb is not None and bce_desc_emb.shape[0] == fu.BCE_EMBEDDING_DIM:
                            updated_concatenated_emb = np.concatenate((clip_img_emb, bce_desc_emb))
                            fu.update_vector_in_index(updated_concatenated_emb, actual_faiss_id) 
                            logging.info(f"图片 ID: {image_db_id} ({original_filename}) Qwen-VL分析完成并更新了FAISS向量。")
                        else:
                            logging.warning(f"图片 ID: {image_db_id} ({original_filename}) Qwen-VL分析的BCE embedding生成失败或维度不符。FAISS向量未更新BCE部分。")
                    else:
                        # 分析失败，图片保持未增强状态，等待后续手动触发
                        error_msg = qwen_result.get("error", "未知错误") if qwen_result else "返回结果为空"
                        logging.warning(f"图片 ID: {image_db_id} ({original_filename}) Qwen-VL分析失败: {error_msg}。图片保持未增强状态，可稍后手动增强。")
                
                # --- 新增/修改开始 ---
                # 在图片处理成功后，调用人脸识别流程
                if app_config.get("face_recognition_enabled", True):
                    logging.info(f"开始对图片 ID: {image_db_id} 进行人脸识别...")
                    # 使用绝对路径调用服务
                    detected_faces = face_service.detect_faces(original_path_abs) 
                    
                    if detected_faces:
                        logging.info(f"在图片 ID: {image_db_id} 中检测到 {len(detected_faces)} 张人脸")
                        cluster_threshold = app_config.get("face_cluster_threshold", 0.5)
                        for i, face in enumerate(detected_faces):
                            feature_vec = face["FeatureData"]
                            logging.debug(f"处理第 {i+1} 张人脸，特征向量维度: {feature_vec.shape}")
                            
                            # 在人脸FAISS中搜索最相似的人脸
                            sims, face_ids = ffu_face.search_vectors_in_index(feature_vec, top_k=1)
                            
                            cluster_id = None
                            # 如果找到了相似人脸且相似度超过阈值
                            if face_ids and sims and sims[0] > cluster_threshold:
                                matched_face_id = face_ids[0]
                                cluster_id = db.get_cluster_id_by_face_id(matched_face_id)
                                if cluster_id:
                                    logging.info(f"找到匹配人脸 (face_id:{matched_face_id}, sim:{sims[0]:.4f})，归入聚类 {cluster_id}")
                                else:
                                    logging.warning(f"数据不一致: 找到匹配人脸 face_id:{matched_face_id} 但未找到其聚类。")
                            else:
                                logging.info(f"未找到相似人脸 (阈值: {cluster_threshold})，将创建新聚类")

                            # 如果未找到匹配或没有聚类ID，则创建新聚类
                            if not cluster_id:
                                cluster_id = db.create_new_face_cluster()
                                logging.info(f"创建了新的人脸聚类 ID: {cluster_id}")

                            attributes_to_collect = ["Age", "Gender", "Glasses", "HeadPose", "Mask"]
                            attributes_dict = {key: face.get(key) for key in attributes_to_collect if face.get(key) is not None}
                            

                            # 将检测到的人脸信息存入数据库
                            new_face_id = db.add_detected_face(
                                image_id=image_db_id,
                                cluster_id=cluster_id,
                                face_box=face.get("FaceBox", []),
                                attributes=attributes_dict, # 使用新构建的字典
                                score=face.get("Score", 0.0)
                            )

                            if new_face_id:
                                logging.info(f"将人脸 ID: {new_face_id} 添加到人脸FAISS索引")
                                # 将新的人脸特征向量添加到人脸FAISS索引中，使用数据库的face_id作为其唯一标识
                                ffu_face.add_vector_to_index(feature_vec, new_face_id)
                        
                        # 批量处理完后保存一次人脸FAISS索引
                        ffu_face.save_faiss_index()
                        logging.info(f"已保存人脸FAISS索引，当前索引大小: {ffu_face.get_face_index_status()}")
                    else:
                        logging.info(f"图片 ID: {image_db_id} 中未检测到人脸")
                # --- 新增/修改结束 ---

                return {
                    "id": image_db_id, 
                    "faiss_id": actual_faiss_id, 
                    "filename": original_filename, 
                    "status": "success"
                }
            else: 
                logging.error(f"图片 '{original_filename}' 添加到FAISS失败。回滚数据库记录。")
                db.hard_delete_image_from_db(image_db_id) 
        else: 
            logging.error(f"图片 '{original_filename}' 存入数据库失败。")

        # Cleanup on failure
        if os.path.exists(original_path_abs): os.remove(original_path_abs)
        if thumbnail_path_abs and os.path.exists(thumbnail_path_abs): os.remove(thumbnail_path_abs)
        return None

    except Exception as e:
        logging.error(f"处理上传图片 '{original_filename}' 时发生严重错误: {e}", exc_info=True)
        if image_db_id: 
            if actual_faiss_id and fu.faiss_index is not None: 
                try: 
                    fu.faiss_index.remove_ids(np.array([actual_faiss_id], dtype='int64'))
                    logging.info(f"FAISS ID {actual_faiss_id} removed during error cleanup.")
                except Exception as fe: logging.error(f"处理错误后FAISS回滚失败: {fe}")
            db.hard_delete_image_from_db(image_db_id) 
        
        if os.path.exists(original_path_abs): os.remove(original_path_abs)
        if thumbnail_path_abs and os.path.exists(thumbnail_path_abs): os.remove(thumbnail_path_abs)
        return None

def batch_enhance_worker():
    """批量增强分析的工作线程函数"""
    global batch_enhance_status
    
    with batch_enhance_lock:
        if batch_enhance_status["is_running"]:
            logging.warning("批量增强分析已在运行中，跳过重复启动。")
            return
            
        batch_enhance_status.update({
            "is_running": True,
            "is_stopped": False,
            "processed_count": 0,
            "current_image_id": None,
            "current_image_filename": None,
            "start_time": time.time(),
            "errors": [],
            "last_error": None
        })
    
    try:
        logging.info("开始批量增强分析...")
        
        # 获取未增强的图片列表
        unenhanced_images = db.get_images_for_enhancement(limit=10000)  # 设置一个较大的限制
        
        with batch_enhance_lock:
            batch_enhance_status["total_images"] = len(unenhanced_images)
        
        if not unenhanced_images:
            logging.info("没有未增强的图片需要处理。")
            with batch_enhance_lock:
                batch_enhance_status["is_running"] = False
            return
        
        logging.info(f"找到 {len(unenhanced_images)} 张未增强的图片，开始处理...")
        
        for image_record in unenhanced_images:
            # 检查是否被停止
            with batch_enhance_lock:
                if batch_enhance_status["is_stopped"]:
                    logging.info("批量增强分析被用户停止。")
                    break
                    
                # 更新当前处理状态
                batch_enhance_status["current_image_id"] = image_record["id"]
                # 从original_path中提取文件名
                original_path = image_record["original_path"]
                batch_enhance_status["current_image_filename"] = os.path.basename(original_path) if original_path else f"ID_{image_record['id']}"
            
            # 执行增强分析
            try:
                # 构建绝对路径
                absolute_original_path = os.path.join(CURRENT_DIR, image_record["original_path"])
                
                if not os.path.exists(absolute_original_path):
                    error_msg = f"图片文件不存在: {absolute_original_path}"
                    logging.warning(error_msg)
                    with batch_enhance_lock:
                        batch_enhance_status["errors"].append({
                            "image_id": image_record["id"], 
                            "error": error_msg
                        })
                        batch_enhance_status["last_error"] = error_msg
                    continue
                
                logging.info(f"正在处理图片 ID: {image_record['id']} - {batch_enhance_status['current_image_filename']}")
                
                # 调用Qwen-VL分析
                qwen_result = qwen_service.analyze_image_content(absolute_original_path)
                
                if qwen_result and qwen_result.get("success") and (qwen_result.get("description") or qwen_result.get("keywords")):
                    # 更新数据库
                    update_success = db.update_image_enhancement(
                        image_record["id"], 
                        qwen_result["description"], 
                        qwen_result["keywords"]
                    )
                    
                    if update_success:
                        # 获取CLIP embedding并更新FAISS
                        clip_img_emb = db.get_clip_embedding_for_image(image_record["id"])
                        if clip_img_emb is not None:
                            bce_desc_emb = bce_service.get_bce_embedding(qwen_result["description"])
                            if bce_desc_emb is not None and bce_desc_emb.shape[0] == fu.BCE_EMBEDDING_DIM:
                                updated_concatenated_emb = np.concatenate((clip_img_emb, bce_desc_emb))
                            else:
                                zeros_bce_emb = np.zeros(fu.BCE_EMBEDDING_DIM, dtype=np.float32)
                                updated_concatenated_emb = np.concatenate((clip_img_emb, zeros_bce_emb))
                            
                            # 更新FAISS向量
                            faiss_id = image_record["faiss_id"] if image_record["faiss_id"] else image_record["id"]
                            fu.update_vector_in_index(updated_concatenated_emb, faiss_id)
                        
                        logging.info(f"图片 ID: {image_record['id']} 增强分析完成。")
                    else:
                        error_msg = f"图片 ID: {image_record['id']} 数据库更新失败"
                        logging.error(error_msg)
                        with batch_enhance_lock:
                            batch_enhance_status["errors"].append({
                                "image_id": image_record["id"], 
                                "error": error_msg
                            })
                            batch_enhance_status["last_error"] = error_msg
                else:
                    # 分析失败
                    error_msg = qwen_result.get("error", "Qwen-VL分析失败") if qwen_result else "分析结果为空"
                    logging.warning(f"图片 ID: {image_record['id']} 增强分析失败: {error_msg}")
                    with batch_enhance_lock:
                        batch_enhance_status["errors"].append({
                            "image_id": image_record["id"], 
                            "error": error_msg
                        })
                        batch_enhance_status["last_error"] = error_msg
                
            except Exception as e:
                error_msg = f"处理图片 ID: {image_record['id']} 时发生异常: {str(e)}"
                logging.error(error_msg, exc_info=True)
                with batch_enhance_lock:
                    batch_enhance_status["errors"].append({
                        "image_id": image_record["id"], 
                        "error": error_msg
                    })
                    batch_enhance_status["last_error"] = error_msg
            
            # 更新处理计数
            with batch_enhance_lock:
                batch_enhance_status["processed_count"] += 1
            
            # 添加小延迟避免过度占用资源
            time.sleep(0.1)
        
        # 保存FAISS索引
        try:
            fu.save_faiss_index()
            logging.info("批量增强分析完成，FAISS索引已保存。")
        except Exception as e:
            logging.error(f"保存FAISS索引失败: {e}")
        
    except Exception as e:
        error_msg = f"批量增强分析过程中发生严重错误: {str(e)}"
        logging.error(error_msg, exc_info=True)
        with batch_enhance_lock:
            batch_enhance_status["last_error"] = error_msg
    
    finally:
        with batch_enhance_lock:
            batch_enhance_status["is_running"] = False
            batch_enhance_status["current_image_id"] = None
            batch_enhance_status["current_image_filename"] = None
        
        logging.info("批量增强分析线程结束。")

# --- API 路由 ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/controls')
def controls_page():
    return render_template('controls.html')

@app.route('/upload_images', methods=['POST'])
def upload_images_api():
    if 'files' not in request.files:
        return jsonify({"error": "请求中未找到文件部分(files key missing)"}), 400
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "未选择任何文件"}), 400

    processed_results = []
    failed_count = 0
    for file_storage in files:
        if file_storage and file_storage.filename: 
            result = process_single_image_upload(file_storage)
            if result:
                processed_results.append(result)
            else:
                failed_count += 1
        else:
            failed_count +=1 
    
    if processed_results:
        fu.save_faiss_index() 
        return jsonify({
            "message": f"成功处理 {len(processed_results)} 张图片，失败 {failed_count} 张。",
            "processed_files": processed_results
        }), 200
    elif failed_count > 0 and not processed_results: 
       return jsonify({"error": f"所有 {failed_count} 张有效图片处理均失败。"}), 500
    else: 
        return jsonify({"error": "未提供有效文件进行处理。"}), 400


@app.route('/search_images', methods=['POST'])
def search_images_api():
    if not clip_model or fu.faiss_index is None:
        return jsonify({"error": "模型或FAISS索引未初始化。"}), 503
    
    data = request.get_json()
    if not data: return jsonify({"error": "请求数据为空"}), 400

    query_text = data.get('query_text', '').strip()
    top_k = int(data.get('top_k', 200)) 
    if not query_text:
        return jsonify({"error": "查询文本不能为空"}), 400

    query_clip_emb = compute_clip_text_embedding(query_text) 
    if query_clip_emb is None:
        return jsonify({"error": "无法计算查询文本的CLIP embedding"}), 500

    use_enhanced = app_config.get("use_enhanced_search", True)
    logging.info(f"搜索模式: {'增强搜索' if use_enhanced else '仅CLIP搜索'}")

    if use_enhanced:
        query_bce_emb = bce_service.get_bce_embedding(query_text)
        if query_bce_emb is None or query_bce_emb.shape[0] != fu.BCE_EMBEDDING_DIM:
            logging.warning(f"增强搜索的BCE embedding生成失败或维度不符。将使用零向量代替BCE部分。")
            query_bce_emb = np.zeros(fu.BCE_EMBEDDING_DIM, dtype=np.float32)
    else:
        query_bce_emb = np.zeros(fu.BCE_EMBEDDING_DIM, dtype=np.float32)
    
    concatenated_query_emb = np.concatenate((query_clip_emb, query_bce_emb))
    
    distances, faiss_ids = fu.search_vectors_in_index(concatenated_query_emb, top_k=top_k)
    results = []
    if not faiss_ids: 
        return jsonify({
            "query": query_text, 
            "results": [], 
            "message": "未找到匹配图片。",
            "search_mode_is_enhanced": use_enhanced
        }), 200

    for i in range(len(faiss_ids)):
        faiss_id_val = int(faiss_ids[i])
        similarity = float(distances[i]) 
        
        image_data = db.get_image_by_faiss_id(faiss_id_val) 
        if image_data:
            try:
                keywords_list = json.loads(image_data["qwen_keywords"]) if image_data["qwen_keywords"] else []
            except (json.JSONDecodeError, TypeError):
                keywords_list = []
            
            try:
                user_tags_list = json.loads(image_data["user_tags"]) if image_data["user_tags"] else []
            except (json.JSONDecodeError, TypeError):
                user_tags_list = []

            # --- MODIFIED: Rebuild absolute path for existence check ---
            thumbnail_path_from_db = image_data['thumbnail_path']
            original_path_from_db = image_data['original_path']
            
            thumbnail_url = f"/thumbnails/{os.path.basename(thumbnail_path_from_db)}" if thumbnail_path_from_db and os.path.exists(os.path.join(CURRENT_DIR, thumbnail_path_from_db)) else None
            original_url = f"/uploads/{os.path.basename(original_path_from_db)}" if original_path_from_db and os.path.exists(os.path.join(CURRENT_DIR, original_path_from_db)) else None

            results.append({
                "id": image_data["id"],
                "faiss_id": image_data["faiss_id"],
                "filename": image_data["original_filename"],
                "thumbnail_url": thumbnail_url,
                "original_url": original_url,
                "similarity": similarity, 
                "qwen_description": image_data["qwen_description"],
                "qwen_keywords": keywords_list,
                "user_tags": user_tags_list, 
                "is_enhanced": image_data["is_enhanced"]
            })
        else:
            logging.warning(f"在数据库中未找到FAISS ID为 {faiss_id_val} 的图片记录 (可能已被删除或不同步)。")
    
    return jsonify({
        "query": query_text, 
        "results": results,
        "search_mode_is_enhanced": use_enhanced
    }), 200

# --- NEW: Image-to-Image Search API ---
@app.route('/search_by_uploaded_image', methods=['POST'])
def search_by_uploaded_image_api():
    if not clip_model:
        return jsonify({"error": "CLIP模型未初始化。"}), 503
    
    if 'image_query_file' not in request.files:
        return jsonify({"error": "请求中未找到图片文件(image_query_file key missing)"}), 400
    
    uploaded_file = request.files['image_query_file']
    if not uploaded_file or uploaded_file.filename == '':
        return jsonify({"error": "未选择图片文件进行搜索"}), 400

    logging.info(f"开始图搜图处理，上传文件名: {uploaded_file.filename}")

    tmp_file_path = None
    query_clip_emb = None
    try:
        # Save to a temporary file to pass its path to compute_clip_image_embedding
        # Suffix helps Pillow determine file type, though compute_clip_image_embedding converts to RGB
        suffix = os.path.splitext(uploaded_file.filename)[1] if os.path.splitext(uploaded_file.filename)[1] else '.tmp'
        with tempfile.NamedTemporaryFile(dir=TEMP_SEARCH_UPLOADS_DIR, suffix=suffix, delete=False) as tmp_file:
            uploaded_file.save(tmp_file.name)
            tmp_file_path = tmp_file.name
        
        logging.info(f"图搜图: 临时文件已保存到 {tmp_file_path}")
        query_clip_emb = compute_clip_image_embedding(tmp_file_path)

    except Exception as e:
        logging.error(f"图搜图: 处理上传图片时发生错误: {e}", exc_info=True)
        return jsonify({"error": f"处理上传图片失败: {e}"}), 500
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.remove(tmp_file_path)
                logging.info(f"图搜图: 临时文件 {tmp_file_path} 已删除。")
            except Exception as e_remove:
                logging.warning(f"图搜图: 无法删除临时文件 {tmp_file_path}: {e_remove}")

    if query_clip_emb is None:
        return jsonify({"error": "无法为上传的图片计算CLIP embedding"}), 500

    # Get all valid CLIP embeddings from the database
    # This list contains dicts: {'id': db_id, 'faiss_id': faiss_id, 'clip_embedding': np.array}
    all_db_images_data = db.get_all_valid_images_clip_embeddings()
    if not all_db_images_data:
        return jsonify({"query_filename": uploaded_file.filename, "results": [], "message": "数据库中没有可比较的图片。"}), 200

    db_clip_embeddings_list = [item['clip_embedding'] for item in all_db_images_data]
    # Stack into a matrix for batch dot product: (N, D)
    db_clip_embeddings_matrix = np.array(db_clip_embeddings_list)

    # Calculate cosine similarities (dot product, since embeddings are normalized)
    # query_clip_emb is (D,), db_clip_embeddings_matrix is (N, D)
    # Result of dot product will be (N,)
    similarities = np.dot(db_clip_embeddings_matrix, query_clip_emb) # Already normalized

    results = []
    SIMILARITY_THRESHOLD = 0.6 # As per requirement

    for i, image_data_item in enumerate(all_db_images_data):
        similarity_score = float(similarities[i])
        
        if similarity_score > SIMILARITY_THRESHOLD:
            # Fetch full image details from DB using its ID
            image_full_details = db.get_image_by_id(image_data_item["id"])
            if image_full_details:
                try:
                    keywords_list = json.loads(image_full_details["qwen_keywords"]) if image_full_details["qwen_keywords"] else []
                except (json.JSONDecodeError, TypeError):
                    keywords_list = []
                try:
                    user_tags_list = json.loads(image_full_details["user_tags"]) if image_full_details["user_tags"] else []
                except (json.JSONDecodeError, TypeError):
                    user_tags_list = []
                
                # --- MODIFIED: Rebuild absolute path for existence check ---
                thumbnail_path_from_db = image_full_details['thumbnail_path']
                original_path_from_db = image_full_details['original_path']

                thumbnail_url = f"/thumbnails/{os.path.basename(thumbnail_path_from_db)}" if thumbnail_path_from_db and os.path.exists(os.path.join(CURRENT_DIR, thumbnail_path_from_db)) else None
                original_url = f"/uploads/{os.path.basename(original_path_from_db)}" if original_path_from_db and os.path.exists(os.path.join(CURRENT_DIR, original_path_from_db)) else None
                
                results.append({
                    "id": image_full_details["id"],
                    "faiss_id": image_full_details["faiss_id"], # Though not used for this search, good to return
                    "filename": image_full_details["original_filename"],
                    "thumbnail_url": thumbnail_url,
                    "original_url": original_url,
                    "similarity": similarity_score, 
                    "qwen_description": image_full_details["qwen_description"],
                    "qwen_keywords": keywords_list,
                    "user_tags": user_tags_list,
                    "is_enhanced": image_full_details["is_enhanced"]
                })
            else:
                logging.warning(f"图搜图: 在数据库中未找到图片ID为 {image_data_item['id']} 的详细记录，尽管其embedding存在。")

    # Sort results by similarity, descending
    results.sort(key=lambda x: x["similarity"], reverse=True)

    logging.info(f"图搜图: 为 '{uploaded_file.filename}' 找到 {len(results)} 张相似图片 (阈值 > {SIMILARITY_THRESHOLD})。")
    
    return jsonify({
        "query_filename": uploaded_file.filename,
        "results": results,
        "search_mode_is_enhanced": False # This is pure CLIP image search
    }), 200


@app.route('/image_details/<int:image_db_id>', methods=['GET'])
def get_image_details_api(image_db_id):
    image_data = db.get_image_by_id(image_db_id) 
    if not image_data:
        return jsonify({"error": f"图片 ID {image_db_id} 未找到"}), 404
    
    try:
        keywords_list = json.loads(image_data["qwen_keywords"]) if image_data["qwen_keywords"] else []
    except (json.JSONDecodeError, TypeError):
        keywords_list = []
    
    try:
        user_tags_list = json.loads(image_data["user_tags"]) if image_data["user_tags"] else []
    except (json.JSONDecodeError, TypeError): 
        user_tags_list = []

    # --- MODIFIED: Rebuild absolute path for existence check ---
    original_path_from_db = image_data['original_path']
    original_url = f"/uploads/{os.path.basename(original_path_from_db)}" if original_path_from_db and os.path.exists(os.path.join(CURRENT_DIR, original_path_from_db)) else None

    details = {
        "id": image_data["id"],
        "filename": image_data["original_filename"],
        "original_url": original_url,
        "qwen_description": image_data["qwen_description"] or "无",
        "qwen_keywords": keywords_list,
        "user_tags": user_tags_list, 
        "is_enhanced": image_data["is_enhanced"],
    }
    return jsonify(details), 200


@app.route('/config/settings', methods=['GET', 'POST'])
def handle_app_settings():
    global app_config
    if request.method == 'GET':
        for key, value in default_app_config.items():
            app_config.setdefault(key, value)
        return jsonify(app_config), 200
    elif request.method == 'POST':
        data = request.get_json()
        if data is None:
            return jsonify({"error": "无效的JSON数据"}), 400
        
        updated_any = False
        
        # 处理布尔值切换
        if 'qwen_vl_analysis_enabled' in data and isinstance(data['qwen_vl_analysis_enabled'], bool):
            app_config['qwen_vl_analysis_enabled'] = data['qwen_vl_analysis_enabled']
            logging.info(f"Qwen-VL全局分析状态已更新为: {app_config['qwen_vl_analysis_enabled']}")
            updated_any = True
            
        if 'use_enhanced_search' in data and isinstance(data['use_enhanced_search'], bool):
            app_config['use_enhanced_search'] = data['use_enhanced_search']
            logging.info(f"使用增强搜索状态已更新为: {app_config['use_enhanced_search']}")
            updated_any = True
        
        # 处理Qwen配置项
        if 'qwen_model_name' in data and isinstance(data['qwen_model_name'], str):
            app_config['qwen_model_name'] = data['qwen_model_name'].strip()
            logging.info(f"Qwen 模型名称已更新为: {app_config['qwen_model_name']}")
            updated_any = True
            
        if 'qwen_api_key' in data and isinstance(data['qwen_api_key'], str):
            app_config['qwen_api_key'] = data['qwen_api_key'].strip()
            logging.info(f"Qwen API Key 已更新。") # 避免在日志中打印密钥
            updated_any = True

        if 'qwen_base_url' in data and isinstance(data['qwen_base_url'], str):
            app_config['qwen_base_url'] = data['qwen_base_url'].strip()
            logging.info(f"Qwen Base URL 已更新为: {app_config['qwen_base_url']}")
            updated_any = True

        # --- 新增/修改开始 ---
        # 处理人脸识别相关配置
        if 'face_recognition_enabled' in data and isinstance(data['face_recognition_enabled'], bool):
            app_config['face_recognition_enabled'] = data['face_recognition_enabled']
            logging.info(f"人脸自动识别状态已更新为: {app_config['face_recognition_enabled']}")
            updated_any = True

        if 'face_api_url' in data and isinstance(data['face_api_url'], str) and data['face_api_url']:
            app_config['face_api_url'] = data['face_api_url'].strip()
            logging.info(f"人脸识别服务URL已更新为: {app_config['face_api_url']}")
            # 更新face_service客户端
            face_service.init_face_client(app_config['face_api_url'])
            updated_any = True

        if 'face_cluster_threshold' in data and isinstance(data['face_cluster_threshold'], (int, float)):
            app_config['face_cluster_threshold'] = data['face_cluster_threshold']
            logging.info(f"人脸聚类阈值已更新为: {app_config['face_cluster_threshold']}")
            updated_any = True
        # --- 新增/修改结束 ---

        if updated_any:
            save_app_config()
            # 如果Qwen配置有变，重新初始化客户端
            qwen_service.init_qwen_client(
                api_key=app_config.get('qwen_api_key'),
                base_url=app_config.get('qwen_base_url'),
                model_name=app_config.get('qwen_model_name')
            )
            return jsonify({"message": "应用设置已更新。", "settings": app_config}), 200
        else:
            return jsonify({"message": "未提供有效设置进行更新。", "settings": app_config}), 200

@app.route('/enhance_image/<int:image_db_id>', methods=['POST'])
def enhance_single_image_api(image_db_id):
    image_data = db.get_image_by_id(image_db_id)
    if not image_data:
        return jsonify({"error": f"图片 ID {image_db_id} 未找到"}), 404
    if image_data["is_enhanced"]: 
        return jsonify({
            "message": f"图片 ID {image_db_id} 已经分析过了。",
            "qwen_description": image_data["qwen_description"],
            "qwen_keywords": json.loads(image_data["qwen_keywords"] or "[]"),
            "is_enhanced": True
            }), 200

    # --- MODIFIED: Rebuild absolute path for file operations ---
    relative_original_path = image_data["original_path"]
    if not relative_original_path:
        return jsonify({"error": f"图片 ID {image_db_id} 的原始文件路径为空。"}), 404
    
    absolute_original_path = os.path.join(CURRENT_DIR, relative_original_path)
    if not os.path.exists(absolute_original_path):
        return jsonify({"error": f"图片 ID {image_db_id} 的原始文件 '{absolute_original_path}' 不存在。"}), 404

    clip_img_emb = db.get_clip_embedding_for_image(image_db_id) 
    if clip_img_emb is None:
        logging.warning(f"图片ID {image_db_id} 在数据库中未找到纯CLIP embedding，尝试重新计算...")
        clip_img_emb = compute_clip_image_embedding(absolute_original_path) # Use absolute path
        if clip_img_emb is None: 
            return jsonify({"error": f"无法获取或计算图片 ID {image_db_id} 的CLIP embedding"}), 500

    logging.info(f"手动触发对图片 ID: {image_db_id} ({absolute_original_path}) 的Qwen-VL分析。")
    qwen_result = qwen_service.analyze_image_content(absolute_original_path) # Use absolute path

    # 检查分析是否成功
    if qwen_result and qwen_result.get("success") and (qwen_result.get("description") or qwen_result.get("keywords")):
        update_success = db.update_image_enhancement(image_db_id, qwen_result["description"], qwen_result["keywords"])
        if not update_success:
             return jsonify({"error": f"图片 ID {image_db_id} 分析结果存入数据库失败。"}), 500

        bce_desc_emb = bce_service.get_bce_embedding(qwen_result["description"])
        if bce_desc_emb is not None and bce_desc_emb.shape[0] == fu.BCE_EMBEDDING_DIM:
            updated_concatenated_emb = np.concatenate((clip_img_emb, bce_desc_emb))
        else: 
            logging.warning(f"BCE embedding for description failed or wrong dim for image {image_db_id}. Using zero vector for BCE part in FAISS.")
            zeros_bce_emb = np.zeros(fu.BCE_EMBEDDING_DIM, dtype=np.float32)
            updated_concatenated_emb = np.concatenate((clip_img_emb, zeros_bce_emb))


        if image_data["faiss_id"] is None: 
            logging.error(f"图片 ID {image_db_id} 在数据库中没有FAISS ID，无法更新FAISS向量。")
            return jsonify({"error": f"图片 ID {image_db_id} 数据不一致，缺少FAISS ID。"}), 500

        if fu.update_vector_in_index(updated_concatenated_emb, image_data["faiss_id"]):
             logging.info(f"图片 ID: {image_db_id} 手动Qwen-VL分析完成并更新了FAISS向量。")
             fu.save_faiss_index()
             return jsonify({
                 "message": f"图片 ID {image_db_id} 分析增强成功。",
                 "qwen_description": qwen_result["description"],
                 "qwen_keywords": qwen_result["keywords"],
                 "is_enhanced": True
                 }), 200
        else: 
            logging.error(f"图片 ID: {image_db_id} FAISS向量更新失败，但DB可能已更新增强状态。")
            return jsonify({
                "error": f"图片 ID {image_db_id} 分析信息已存DB，但FAISS更新失败。",
                "qwen_description": qwen_result["description"],
                "qwen_keywords": qwen_result["keywords"],
                "is_enhanced": True 
                }), 500
    else: 
        # 分析失败，返回错误信息
        error_msg = qwen_result.get("error", "未知错误") if qwen_result else "返回结果为空"
        logging.warning(f"图片 ID: {image_db_id} 手动Qwen-VL分析失败: {error_msg}")
        return jsonify({"error": f"图片 ID {image_db_id} 分析失败: {error_msg}"}), 500

@app.route('/batch_enhance/status', methods=['GET'])
def get_batch_enhance_status_api():
    """获取批量增强分析状态"""
    global batch_enhance_status
    with batch_enhance_lock:
        # 复制状态数据以避免并发修改
        status_copy = batch_enhance_status.copy()
        
        # 转换时间戳为可读格式
        if status_copy.get("start_time"):
            import time
            elapsed_time = time.time() - status_copy["start_time"]
            status_copy["elapsed_time"] = round(elapsed_time, 2)
        
        return jsonify(status_copy), 200

@app.route('/batch_enhance/start', methods=['POST'])
def start_batch_enhance_api():
    """启动批量增强分析"""
    global batch_enhance_thread
    
    with batch_enhance_lock:
        if batch_enhance_status["is_running"]:
            return jsonify({
                "success": False, 
                "error": "批量增强分析已在运行中"
            }), 400
            
        # 检查Qwen-VL服务是否可用
        if not qwen_service.client:
            return jsonify({
                "success": False,
                "error": "Qwen-VL服务未配置，请先在控制面板中配置API Key、Base URL和模型名称"
            }), 503
            
        # 检查是否有未增强的图片
        unenhanced_count = len(db.get_images_for_enhancement(limit=1))
        if unenhanced_count == 0:
            return jsonify({
                "success": False,
                "error": "当前没有需要增强分析的图片"
            }), 400
    
    try:
        # 启动批量增强分析线程
        batch_enhance_thread = threading.Thread(target=batch_enhance_worker, daemon=True)
        batch_enhance_thread.start()
        
        logging.info("批量增强分析线程已启动")
        return jsonify({
            "success": True,
            "message": "批量增强分析已启动"
        }), 200
        
    except Exception as e:
        logging.error(f"启动批量增强分析失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"启动失败: {str(e)}"
        }), 500

@app.route('/batch_enhance/stop', methods=['POST'])
def stop_batch_enhance_api():
    """停止批量增强分析"""
    global batch_enhance_status
    
    with batch_enhance_lock:
        if not batch_enhance_status["is_running"]:
            return jsonify({
                "success": False,
                "error": "当前没有正在运行的批量增强分析"
            }), 400
            
        # 设置停止标志
        batch_enhance_status["is_stopped"] = True
        
        logging.info("用户请求停止批量增强分析")
        return jsonify({
            "success": True,
            "message": "正在停止批量增强分析..."
        }), 200

@app.route('/images', methods=['GET'])
def get_images_list_api():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int) 
    images, total_count = db.get_all_images(page, limit) 
    results = []
    for img_row in images:
        try:
            user_tags_list = json.loads(img_row["user_tags"]) if img_row["user_tags"] else []
        except (json.JSONDecodeError, TypeError):
            user_tags_list = []

        # --- MODIFIED: Rebuild absolute path for existence check ---
        relative_original_path = img_row['original_path']
        relative_thumbnail_path = img_row['thumbnail_path']

        thumbnail_url = f"/thumbnails/{os.path.basename(relative_thumbnail_path)}" if relative_thumbnail_path and os.path.exists(os.path.join(CURRENT_DIR, relative_thumbnail_path)) else None
        original_url = f"/uploads/{os.path.basename(relative_original_path)}" if relative_original_path and os.path.exists(os.path.join(CURRENT_DIR, relative_original_path)) else None

        results.append({
            "id": img_row["id"],
            "filename": img_row["original_filename"],
            "thumbnail_url": thumbnail_url,
            "original_url": original_url,
            "is_enhanced": img_row["is_enhanced"],
            "user_tags": user_tags_list, 
        })
    return jsonify({
        "images": results,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit if limit > 0 else 0
    })

@app.route('/delete_images_batch', methods=['POST'])
def delete_images_batch_api():
    data = request.get_json()
    if not data or 'image_ids' not in data or not isinstance(data['image_ids'], list):
        return jsonify({"error": "无效的请求数据，需要包含 image_ids 列表。"}), 400

    image_ids_to_delete = data['image_ids']
    if not image_ids_to_delete:
        return jsonify({"error": "未提供要删除的图片ID。"}), 400

    face_ids_to_remove_from_faiss = db.get_face_ids_by_image_ids(image_ids_to_delete)

    deleted_count = 0
    failed_ids = []
    faiss_ids_to_remove_from_index = []

    for image_id in image_ids_to_delete:
        try:
            image_id_int = int(image_id)
            # --- MODIFIED: Paths from DB are relative, rebuild to absolute for deletion ---
            relative_original_path, relative_thumbnail_path, faiss_id = db.get_image_paths_and_faiss_id(image_id_int)

            if relative_original_path:
                absolute_original_path = os.path.join(CURRENT_DIR, relative_original_path)
                if os.path.exists(absolute_original_path):
                    os.remove(absolute_original_path)
                    logging.info(f"已删除原始图片文件: {absolute_original_path}")
                else:
                    logging.warning(f"原始图片文件未找到，无法删除: {absolute_original_path} for ID {image_id_int}")
            
            if relative_thumbnail_path:
                absolute_thumbnail_path = os.path.join(CURRENT_DIR, relative_thumbnail_path)
                if os.path.exists(absolute_thumbnail_path):
                    os.remove(absolute_thumbnail_path)
                    logging.info(f"已删除缩略图文件: {absolute_thumbnail_path}")
                else:
                    logging.warning(f"缩略图文件未找到，无法删除: {absolute_thumbnail_path} for ID {image_id_int}")

            if faiss_id is not None:
                faiss_ids_to_remove_from_index.append(faiss_id)
            
            # 数据库的外键已设置为 ON DELETE CASCADE,
            if db.hard_delete_image_from_db(image_id_int):
                deleted_count += 1
            else:
                failed_ids.append(image_id_int)
                logging.error(f"从数据库删除图片 ID {image_id_int} 失败。")

        except ValueError:
            logging.error(f"无效的图片ID格式: {image_id}")
            failed_ids.append(image_id)
        except Exception as e:
            logging.error(f"删除图片 ID {image_id} 时发生错误: {e}", exc_info=True)
            failed_ids.append(image_id)
    
    if faiss_ids_to_remove_from_index:
        if fu.faiss_index is not None and fu.faiss_index.ntotal > 0:
            try:
                logging.info(f"准备从FAISS中删除ID列表: {faiss_ids_to_remove_from_index}")
                ids_to_remove_np = np.array(faiss_ids_to_remove_from_index, dtype=np.int64)
                num_removed = fu.faiss_index.remove_ids(ids_to_remove_np)
                logging.info(f"从FAISS索引中移除了 {num_removed} 个向量。")
                if num_removed > 0 : fu.save_faiss_index()
            except Exception as e_faiss_remove:
                logging.error(f"从FAISS索引移除向量时出错: {e_faiss_remove}")
        else:
            logging.warning("FAISS索引为空或未初始化，跳过FAISS删除。")
            
    # 从人脸FAISS索引中删除对应向量
    if face_ids_to_remove_from_faiss:
        logging.info(f"准备从人脸FAISS中删除ID列表: {face_ids_to_remove_from_faiss}")
        ffu_face.remove_vectors_from_index(face_ids_to_remove_from_faiss)

    if deleted_count > 0:
        return jsonify({
            "success": True, 
            "message": f"成功删除 {deleted_count} 张图片。",
            "failed_ids": failed_ids
        }), 200
    else:
        return jsonify({
            "success": False, 
            "error": "未能删除任何图片。",
            "failed_ids": failed_ids
        }), 500

@app.route('/add_user_tags_batch', methods=['POST'])
def add_user_tags_batch_api():
    data = request.get_json()
    if not data or 'image_ids' not in data or not isinstance(data['image_ids'], list) \
            or 'user_tags' not in data or not isinstance(data['user_tags'], list):
        return jsonify({"error": "无效的请求数据，需要包含 image_ids (列表) 和 user_tags (字符串列表)。"}), 400

    image_ids_to_tag = data['image_ids']
    user_tags_to_add = [str(tag).strip() for tag in data['user_tags'] if str(tag).strip()] 

    if not image_ids_to_tag:
        return jsonify({"error": "未提供要标记的图片ID。"}), 400
    if not user_tags_to_add:
        return jsonify({"error": "未提供有效的用户标签。"}), 400
    
    updated_count = 0
    failed_ids = []

    for image_id in image_ids_to_tag:
        try:
            image_id_int = int(image_id)
            if db.update_user_tags_for_image(image_id_int, user_tags_to_add):
                updated_count += 1
            else:
                failed_ids.append(image_id_int)
        except ValueError:
            logging.error(f"无效的图片ID格式: {image_id} for tagging.")
            failed_ids.append(image_id)
        except Exception as e:
            logging.error(f"为图片 ID {image_id} 添加标签时发生错误: {e}", exc_info=True)
            failed_ids.append(image_id)
            
    if updated_count > 0:
        return jsonify({
            "success": True, 
            "message": f"成功为 {updated_count} 张图片添加/更新了用户标签。",
            "failed_ids": failed_ids
        }), 200
    else:
        return jsonify({
            "success": False, 
            "error": "未能为任何图片添加/更新用户标签。",
            "failed_ids": failed_ids
        }), 500


# 新增人脸相关 API 路由
@app.route('/faces/search_by_face', methods=['POST'])
def search_images_by_face_api():
    """
    图搜人脸：上传一张带有人脸的图片，返回包含该人脸的所有相册图片。
    """
    if 'face_query_file' not in request.files:
        return jsonify({"error": "请求中未找到人脸查询文件(face_query_file key missing)"}), 400
    
    query_file = request.files['face_query_file']
    if not query_file or query_file.filename == '':
        return jsonify({"error": "未选择人脸查询文件"}), 400

    logging.info(f"开始通过人脸图片 '{query_file.filename}' 进行搜索...")

    # 使用临时文件处理上传的图片
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=os.path.splitext(query_file.filename)[1]) as tmp_file:
            query_file.save(tmp_file.name)
            # 对查询图片进行人脸检测
            detected_faces = face_service.detect_faces(tmp_file.name)
    except Exception as e:
        logging.error(f"处理人脸查询图片时出错: {e}", exc_info=True)
        return jsonify({"error": "处理查询图片失败。"}), 500

    if not detected_faces:
        return jsonify({"error": "在您上传的图片中未能检测到人脸，或服务出错。"}), 400
    
    # 默认使用检测到的第一张、质量最高的人脸进行搜索
    query_face = max(detected_faces, key=lambda x: x.get('Score', 0))
    query_feature_vec = query_face["FeatureData"]
    
    # 在FAISS中搜索最相似的人脸，以确定其聚类ID
    sims, face_ids = ffu_face.search_vectors_in_index(query_feature_vec, top_k=1)
    
    if not face_ids:
        return jsonify({"message": "未在图库中找到任何相似的人脸。", "results": []}), 200
        
    # 根据最匹配的人脸ID找到其所属的聚类ID
    target_cluster_id = db.get_cluster_id_by_face_id(face_ids[0])
    if not target_cluster_id:
        return jsonify({"error": "数据不一致：找到了匹配的人脸但无法找到其聚类信息。"}), 500

    # 根据聚类ID，分页获取所有包含该人脸的图片信息
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    # 注意：您需要在 database_utils.py 中实现 get_images_by_cluster_id 函数
    images_data, total_count = db.get_images_by_cluster_id(target_cluster_id, page, limit)
    
    results = []
    for img_row in images_data:
        thumbnail_url = f"/thumbnails/{os.path.basename(img_row['thumbnail_path'])}" if img_row['thumbnail_path'] and os.path.exists(os.path.join(CURRENT_DIR, img_row['thumbnail_path'])) else None
        original_url = f"/uploads/{os.path.basename(img_row['original_path'])}" if img_row['original_path'] and os.path.exists(os.path.join(CURRENT_DIR, img_row['original_path'])) else None
        results.append({
            "id": img_row["id"],
            "filename": img_row["original_filename"],
            "thumbnail_url": thumbnail_url,
            "original_url": original_url,
        })

    return jsonify({
        "message": f"找到了属于聚类 {target_cluster_id} 的 {total_count} 张图片。",
        "cluster_id": target_cluster_id,
        "results": results,
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "total_pages": (total_count + limit - 1) // limit if limit > 0 else 0
    }), 200

# --- 新增/修改结束 ---


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    if ".." in filename or filename.startswith("/"):
        return jsonify({"error": "非法路径"}), 400
    return send_from_directory(UPLOADS_DIR, filename)

@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    if ".." in filename or filename.startswith("/"):
        return jsonify({"error": "非法路径"}), 400
    return send_from_directory(THUMBNAILS_DIR, filename)


# --- 新增API路由 ---
@app.route('/faces/clusters', methods=['GET'])
def get_face_clusters():
    """
    获取所有人脸聚类信息列表。
    注意: 需要在 database_utils.py 中实现 get_all_face_clusters 函数。
    """
    try:
        # 这个DB函数需要返回一个列表，每个元素包含 cluster_id, name, face_count, 和 cover_thumbnail_path
        clusters_data = db.get_all_face_clusters() 
        results = []
        for cluster in clusters_data:
            thumbnail_url = None
            if cluster.get('cover_thumbnail_path'):
                thumbnail_url = f"/thumbnails/{os.path.basename(cluster['cover_thumbnail_path'])}"
            results.append({
                "cluster_id": cluster['cluster_id'],
                "name": cluster.get('name'), # .get()确保即使name为None也不会报错
                "face_count": cluster.get('face_count', 0),
                "cover_thumbnail_url": thumbnail_url
            })
        return jsonify({"clusters": results}), 200
    except Exception as e:
        logging.error(f"获取人脸聚类时出错: {e}", exc_info=True)
        return jsonify({"error": "获取人脸聚类信息失败。"}), 500

@app.route('/faces/clusters/<int:cluster_id>', methods=['PUT'])
def update_face_cluster_name(cluster_id):
    """
    更新一个人脸聚类的名称。
    注意: 需要在 database_utils.py 中实现 update_face_cluster_name 函数。
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "请求体中缺少 'name' 字段。"}), 400
    
    new_name = data['name'].strip()
    if not new_name:
        return jsonify({"error": "'name' 字段不能为空。"}), 400

    try:
        if db.update_face_cluster_name(cluster_id, new_name):
            return jsonify({"message": f"聚类 {cluster_id} 名称已更新为 '{new_name}'。"}), 200
        else:
            return jsonify({"error": f"未能找到或更新聚类ID {cluster_id}。"}), 404
    except Exception as e:
        logging.error(f"更新聚类名称时出错: {e}", exc_info=True)
        return jsonify({"error": "更新聚类名称失败。"}), 500

@app.route('/faces/clusters/<int:cluster_id>/images', methods=['GET'])
def get_images_for_cluster(cluster_id):
    """
    分页获取指定人脸聚类下的所有图片。
    注意: get_images_by_cluster_id 函数已在之前添加。
    """
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    try:
        images_data, total_count = db.get_images_by_cluster_id(cluster_id, page, limit)
        results = []
        for img_row in images_data:
            thumbnail_url = f"/thumbnails/{os.path.basename(img_row['thumbnail_path'])}" if img_row['thumbnail_path'] and os.path.exists(os.path.join(CURRENT_DIR, img_row['thumbnail_path'])) else None
            original_url = f"/uploads/{os.path.basename(img_row['original_path'])}" if img_row['original_path'] and os.path.exists(os.path.join(CURRENT_DIR, img_row['original_path'])) else None
            results.append({
                "id": img_row["id"],
                "filename": img_row["original_filename"],
                "thumbnail_url": thumbnail_url,
                "original_url": original_url,
            })
        return jsonify({
            "message": f"找到了属于聚类 {cluster_id} 的 {total_count} 张图片。",
            "cluster_id": cluster_id,
            "results": results,
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": (total_count + limit - 1) // limit if limit > 0 else 0
        }), 200
    except Exception as e:
        logging.error(f"获取聚类图片时出错: {e}", exc_info=True)
        return jsonify({"error": "获取聚类图片失败。"}), 500

@app.route('/faces/search', methods=['GET'])
def search_faces_by_name():
    """
    通过人名搜索图片。
    注意: 需要在 database_utils.py 中实现 get_images_by_cluster_name 函数。
    """
    name_query = request.args.get('name', '').strip()
    if not name_query:
        return jsonify({"error": "需要提供 'name' 查询参数。"}), 400
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)

    try:
        # 这个DB函数需要能处理模糊匹配并返回分页的图片列表和总数
        images_data, total_count = db.get_images_by_cluster_name(name_query, page, limit)
        results = []
        for img_row in images_data:
            thumbnail_url = f"/thumbnails/{os.path.basename(img_row['thumbnail_path'])}" if img_row['thumbnail_path'] and os.path.exists(os.path.join(CURRENT_DIR, img_row['thumbnail_path'])) else None
            original_url = f"/uploads/{os.path.basename(img_row['original_path'])}" if img_row['original_path'] and os.path.exists(os.path.join(CURRENT_DIR, img_row['original_path'])) else None
            results.append({
                "id": img_row["id"],
                "filename": img_row["original_filename"],
                "thumbnail_url": thumbnail_url,
                "original_url": original_url,
            })
        return jsonify({
            "message": f"为 '{name_query}' 找到了 {total_count} 张图片。",
            "query": name_query,
            "results": results,
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": (total_count + limit - 1) // limit if limit > 0 else 0
        }), 200
    except Exception as e:
        logging.error(f"按名称搜索人脸时出错: {e}", exc_info=True)
        return jsonify({"error": "按名称搜索人脸失败。"}), 500

# --- 新增API路由结束 ---


def argsparser():
    parser = argparse.ArgumentParser(prog=__file__)
    parser.add_argument('--image_model', type=str, default='./models/BM1684X/cn_clip_image_vit_h_14_bm1684x_f16_1b.bmodel', help='path of image bmodel')
    parser.add_argument('--text_model', type=str, default='./models/BM1684X/cn_clip_text_vit_h_14_bm1684x_f16_1b.bmodel', help='path of text bmodel')
    parser.add_argument('--bce_model', type=str, default='./models/BM1684X/text2vec_base_chinese_bm1684x_f16_1b.bmodel', help='path of bce bmodel')
    parser.add_argument('--dev_id', type=int, default=0, help='dev id')
    args = parser.parse_args()
    return args



# --- 应用启动 ---
if __name__ == '__main__':
    args = argsparser()
    if getattr(sys, 'frozen', False):
        # 如果是打包后的程序，所有命令行指定的相对路径都需要
        # 转换为 _MEIPASS 临时目录下的绝对路径
        base_path = sys._MEIPASS
        
        # 修正 image_model 路径
        # os.path.normpath an d os.path.basename are used to handle './' prefix
        model_rel_path = os.path.normpath(args.image_model)
        args.image_model = os.path.join(base_path, model_rel_path)

        # 修正 text_model 路径
        model_rel_path = os.path.normpath(args.text_model)
        args.text_model = os.path.join(base_path, model_rel_path)
        
        # 修正 bce_model 路径
        model_rel_path = os.path.normpath(args.bce_model)
        args.bce_model = os.path.join(base_path, model_rel_path)

        logging.info(f"Packaged App: Corrected image_model path to {args.image_model}")
        logging.info(f"Packaged App: Corrected text_model path to {args.text_model}")
        logging.info(f"Packaged App: Corrected bce_model path to {args.bce_model}")
    
    load_app_config()
    db.init_db() 
    fu.init_faiss_index() 

    # --- 新增/修改开始 ---
    # 初始化人脸服务和人脸FAISS索引
    ffu_face.init_faiss_index()
    face_service.init_face_client(app_config.get('face_api_url'))
    # --- 新增/修改结束 ---

    qwen_service.init_qwen_client(
        api_key=app_config.get('qwen_api_key'),
        base_url=app_config.get('qwen_base_url'),
        model_name=app_config.get('qwen_model_name')
    )

    load_clip_model_on_startup(args)
    load_bce_model_on_startup(args)
    
    if not bce_service: 
        logging.warning("BCE模型在bce_service中未能加载。请检查日志。")
    if not clip_model:
        logging.warning("CLIP模型未能加载,请检查日志。")

    logging.info("智能相册后端服务准备启动...")
    app.run(host="0.0.0.0", port=18088, debug=False)