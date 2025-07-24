# faiss_face_utils.py
import faiss
import numpy as np
import os
import logging

FAISS_FACE_INDEX_PATH = os.path.join("data", "album_face_faiss.index")
# 假设人脸识别模型输出512维特征向量，请根据您的模型实际输出进行修改。
# 一个float32占4字节, 如果特征base64解码后是2048字节, 维度就是 2048 / 4 = 512。
FACE_FEATURE_DIM = 512 

faiss_face_index = None

def init_faiss_index():
    global faiss_face_index
    os.makedirs(os.path.dirname(FAISS_FACE_INDEX_PATH), exist_ok=True)
    try:
        if os.path.exists(FAISS_FACE_INDEX_PATH):
            logging.info(f"正在从 {FAISS_FACE_INDEX_PATH} 加载人脸FAISS索引...")
            faiss_face_index = faiss.read_index(FAISS_FACE_INDEX_PATH)
            logging.info(f"人脸FAISS索引加载成功。索引中向量数量: {faiss_face_index.ntotal}, 维度: {faiss_face_index.d}")
            if faiss_face_index.d != FACE_FEATURE_DIM:
                logging.warning(f"警告: 加载的人脸FAISS索引维度 ({faiss_face_index.d}) 与期望维度 ({FACE_FEATURE_DIM}) 不符! 将创建新索引。")
                faiss_face_index = None
        
        if faiss_face_index is None:
            logging.info(f"正在创建新的人脸FAISS索引，维度: {FACE_FEATURE_DIM}")
            # 使用 IndexFlatIP (内积) 进行相似度搜索，适用于归一化后的特征向量
            quantizer = faiss.IndexFlatIP(FACE_FEATURE_DIM)
            # IndexIDMap2 允许我们使用自定义的数据库ID (detected_faces.face_id)
            faiss_face_index = faiss.IndexIDMap2(quantizer)
            logging.info("新的人脸FAISS索引创建成功。")

    except Exception as e:
        logging.error(f"初始化或加载人脸FAISS索引失败: {e}", exc_info=True)
        quantizer = faiss.IndexFlatIP(FACE_FEATURE_DIM)
        faiss_face_index = faiss.IndexIDMap2(quantizer)
        logging.info("已创建一个空的备用人脸FAISS索引。")

def add_vector_to_index(vector: np.ndarray, vector_id: int):
    global faiss_face_index
    if faiss_face_index is None:
        logging.debug("[Face FAISS] 索引未初始化，尝试重新初始化...")
        init_faiss_index()
        
    if faiss_face_index is None:
        logging.error("[Face FAISS] 索引未初始化。无法添加向量。")
        return False
    try:
        # 归一化向量
        vector = vector / np.linalg.norm(vector)
        if vector.ndim == 1:
            vector = np.expand_dims(vector, axis=0) # (1, dim)
        
        vector_id_np = np.array([vector_id], dtype='int64')
        faiss_face_index.add_with_ids(vector.astype(np.float32), vector_id_np)
        logging.info(f"[Face FAISS] 人脸向量 (DB face_id: {vector_id}) 已添加到索引。当前大小: {faiss_face_index.ntotal}")
        return True
    except Exception as e:
        logging.error(f"[Face FAISS] 添加向量到索引失败 (ID: {vector_id}): {e}")
        return False

def search_vectors_in_index(query_vector: np.ndarray, top_k: int = 5):
    global faiss_face_index
    if faiss_face_index is None:
        logging.debug("[Face FAISS] 索引未初始化，尝试重新初始化...")
        init_faiss_index()
        
    if faiss_face_index is None or faiss_face_index.ntotal == 0:
        logging.debug("[Face FAISS] 索引未初始化或为空，这在首次使用时是正常的。")
        return [], []
    try:
        # 归一化查询向量
        query_vector = query_vector / np.linalg.norm(query_vector)
        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)
        
        actual_top_k = min(top_k, faiss_face_index.ntotal)
        if actual_top_k == 0: return [], []

        # distances是内积相似度, indices是对应的face_id
        distances, indices = faiss_face_index.search(query_vector.astype(np.float32), actual_top_k)
        return distances[0].tolist(), indices[0].tolist()
    except Exception as e:
        logging.error(f"[Face FAISS] 搜索向量失败: {e}", exc_info=True)
        return [], []

def save_faiss_index():
    global faiss_face_index
    if faiss_face_index is None:
        return
    try:
        faiss.write_index(faiss_face_index, FAISS_FACE_INDEX_PATH)
        logging.info(f"人脸FAISS索引已保存到 {FAISS_FACE_INDEX_PATH}")
    except Exception as e:
        logging.error(f"保存人脸FAISS索引失败: {e}", exc_info=True)

def remove_vectors_from_index(face_ids: list[int]):
    global faiss_face_index
    if faiss_face_index is None or not face_ids:
        return 0
    try:
        ids_to_remove_np = np.array(face_ids, dtype=np.int64)
        num_removed = faiss_face_index.remove_ids(ids_to_remove_np)
        logging.info(f"[Face FAISS] 从索引中移除了 {num_removed} 个向量。")
        if num_removed > 0:
            save_faiss_index()
        return num_removed
    except Exception as e:
        logging.error(f"[Face FAISS] 从索引移除向量时出错: {e}", exc_info=True)
        return 0

def get_face_index_status():
    """获取人脸FAISS索引的状态信息"""
    global faiss_face_index
    if faiss_face_index is None:
        return {"initialized": False, "total_vectors": 0, "dimension": FACE_FEATURE_DIM}
    return {
        "initialized": True, 
        "total_vectors": faiss_face_index.ntotal, 
        "dimension": faiss_face_index.d
    }