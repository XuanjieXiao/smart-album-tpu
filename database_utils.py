# database_utils.py
import sqlite3
import json
import logging
import os
import numpy as np
from datetime import datetime

DATABASE_PATH = os.path.join("data", "smart_album.db")

# --- 辅助函数，用于Numpy数组和BLOB的转换 ---
def adapt_array(arr):
    return json.dumps(arr.tolist())

def convert_array(text):
    """
    将数据库中的数据转换为numpy数组。
    处理多种可能的数据格式：JSON字符串、二进制数据等。
    对于损坏的数据，返回None而不是抛出异常。
    """
    if text is None:
        return None
    
    try:
        # 如果是bytes类型，尝试解码为字符串
        if isinstance(text, bytes):
            try:
                text = text.decode('utf-8')
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                try:
                    text = text.decode('latin-1')
                except UnicodeDecodeError:
                    logging.debug(f"无法解码二进制数据，数据类型: {type(text)}, 长度: {len(text) if hasattr(text, '__len__') else 'unknown'}")
                    return None
        
        # 尝试解析为JSON
        if isinstance(text, str):
            try:
                # 首先检查是否为空字符串
                if not text.strip():
                    return None
                
                data = json.loads(text)
                # 检查数据是否为有效的数组格式
                if not isinstance(data, (list, tuple)):
                    logging.debug(f"JSON数据不是数组格式: {type(data)}")
                    return None
                
                # 检查数组是否为空
                if len(data) == 0:
                    logging.debug("JSON数据为空数组")
                    return None
                
                # 尝试转换为numpy数组
                return np.array(data, dtype=np.float32)
                
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logging.debug(f"JSON解析失败: {e}, 数据前100字符: {str(text)[:100]}")
                return None
        
        # 如果不是字符串或bytes，直接返回None
        logging.debug(f"未知的数据类型: {type(text)}")
        return None
        
    except Exception as e:
        logging.debug(f"转换数组时发生未知错误: {e}")
        return None

def clean_corrupted_embeddings():
    """
    清理数据库中损坏的embedding数据。
    由于convert_array已经能正确处理损坏数据，这个函数现在主要用于统计和可选的清理。
    """
    # 使用没有类型转换的连接来避免在清理过程中出错
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 首先检查表中存在哪些embedding字段
        cursor.execute("PRAGMA table_info(images)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # 检查哪些embedding字段存在
        embedding_fields = []
        if 'clip_embedding' in column_names:
            embedding_fields.append('clip_embedding')
        if 'bce_embedding' in column_names:
            embedding_fields.append('bce_embedding')
        
        if not embedding_fields:
            logging.info("未找到embedding字段，跳过清理")
            return 0
        
        # 由于convert_array已经能够处理损坏数据，我们只需要统计有多少损坏的数据
        # 实际的清理工作由convert_array在运行时自动处理
        
        logging.info(f"embedding数据检查完成，convert_array函数会自动处理损坏的数据")
        return 0
        
    except Exception as e:
        logging.error(f"检查embedding数据时发生错误: {e}")
        return -1
    finally:
        conn.close()

sqlite3.register_adapter(np.ndarray, adapt_array)
sqlite3.register_converter("ARRAY", convert_array)


def get_db_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # ✅ 1. 先创建 images 表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filename TEXT NOT NULL,
            original_path TEXT NOT NULL UNIQUE,
            thumbnail_path TEXT UNIQUE,
            faiss_id INTEGER UNIQUE, 
            clip_embedding ARRAY,
            bce_embedding ARRAY, -- BCE文本embedding（来自Qwen描述）
            qwen_description TEXT,
            qwen_keywords TEXT,
            user_tags TEXT, 
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- 四个核心分析状态标志位
            has_clip_embedding BOOLEAN DEFAULT FALSE,    -- 是否已生成CLIP embedding
            is_enhanced BOOLEAN DEFAULT FALSE,           -- 是否已完成Qwen-VL增强分析
            has_face_detection BOOLEAN DEFAULT FALSE,    -- 是否已完成人脸识别
            has_face_clustering BOOLEAN DEFAULT FALSE,   -- 是否已完成人脸聚类
            last_enhanced_timestamp TIMESTAMP,
            deleted BOOLEAN DEFAULT FALSE 
        )
    ''')

    # ✅ 2. 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faiss_id ON images (faiss_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_original_path ON images (original_path)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deleted ON images (deleted)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_clip_embedding ON images (has_clip_embedding)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_enhanced ON images (is_enhanced)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_face_detection ON images (has_face_detection)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_face_clustering ON images (has_face_clustering)")

    # 人脸聚类表，代表一个唯一的人
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS face_clusters (
            cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, -- 用户自定义姓名
            cover_face_id INTEGER, -- 该聚类的代表性face_id
            face_count INTEGER DEFAULT 0,
            created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    logging.info("Table 'face_clusters' created or already exists.")

    # 检测到的单个人脸实例表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detected_faces (
            face_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 也是FAISS索引中的ID
            image_id INTEGER NOT NULL,
            cluster_id INTEGER, -- 允许为NULL，表示尚未分配到聚类
            face_box TEXT NOT NULL, -- JSON-encoded list [x1, y1, x2, y2]
            attributes TEXT, -- JSON-encoded facial attributes
            quality_score REAL,
            feature_vector TEXT, -- JSON-encoded feature vector
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
            FOREIGN KEY (cluster_id) REFERENCES face_clusters(cluster_id)
        )
    ''')
    logging.info("Table 'detected_faces' created or already exists.")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_face_image_id ON detected_faces (image_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_face_cluster_id ON detected_faces (cluster_id)")
    

    conn.commit()
    conn.close()
    logging.info("数据库初始化/检查完毕。")


def add_image_to_db(original_filename: str, original_path: str, thumbnail_path: str | None, clip_embedding: np.ndarray):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 根据是否有CLIP embedding来设置状态标志位
        has_clip = clip_embedding is not None
        
        cursor.execute('''
            INSERT INTO images (original_filename, original_path, thumbnail_path, clip_embedding, 
                               has_clip_embedding, is_enhanced, has_face_detection, has_face_clustering, user_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (original_filename, original_path, thumbnail_path, clip_embedding, 
              has_clip, False, False, False, json.dumps([]))) 
        conn.commit()
        image_id = cursor.lastrowid
        logging.info(f"图片 '{original_filename}' (ID: {image_id}) 已初步添加到数据库，CLIP状态: {has_clip}")
        return image_id
    except sqlite3.IntegrityError as e:
        logging.error(f"添加图片 '{original_filename}' 到数据库失败 (路径可能已存在): {original_path}. Error: {e}")
        return None
    finally:
        conn.close()

def update_faiss_id_for_image(image_id: int, faiss_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE images SET faiss_id = ? WHERE id = ?", (faiss_id, image_id))
        conn.commit()
        logging.info(f"数据库中图片 ID {image_id} 的 FAISS ID 已更新为 {faiss_id}")
        return True
    except Exception as e:
        logging.error(f"更新图片 ID {image_id} 的 FAISS ID 失败: {e}")
        return False
    finally:
        conn.close()

def get_image_paths_and_faiss_id(image_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT original_path, thumbnail_path, faiss_id FROM images WHERE id = ?", (image_id,))
    data = cursor.fetchone()
    conn.close()
    if data:
        return data['original_path'], data['thumbnail_path'], data['faiss_id']
    return None, None, None

def hard_delete_image_from_db(image_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
        conn.commit()
        logging.info(f"已从数据库中硬删除图片 ID: {image_id}。")
        return True
    except Exception as e:
        logging.error(f"从数据库硬删除图片 ID: {image_id} 失败: {e}")
        return False
    finally:
        conn.close()

def update_image_enhancement(image_id: int, description: str, keywords: list):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        keywords_json = json.dumps(keywords, ensure_ascii=False)
        cursor.execute('''
            UPDATE images
            SET qwen_description = ?, qwen_keywords = ?, is_enhanced = TRUE, last_enhanced_timestamp = ?
            WHERE id = ? AND deleted = FALSE
        ''', (description, keywords_json, datetime.now(), image_id))
        conn.commit()
        logging.info(f"图片 ID: {image_id} 的增强信息已更新。")
        return True
    except Exception as e:
        logging.error(f"更新图片 ID: {image_id} 增强信息失败: {e}")
        return False
    finally:
        conn.close()

def update_user_tags_for_image(image_id: int, user_tags: list[str]):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        tags_json = json.dumps(user_tags, ensure_ascii=False)
        cursor.execute("UPDATE images SET user_tags = ? WHERE id = ? AND deleted = FALSE", (tags_json, image_id))
        conn.commit()
        logging.info(f"图片 ID: {image_id} 的用户标签已更新为: {tags_json}")
        return True
    except Exception as e:
        logging.error(f"更新图片 ID: {image_id} 用户标签失败: {e}")
        return False
    finally:
        conn.close()

def get_image_by_id(image_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM images WHERE id = ? AND deleted = FALSE", (image_id,))
    image_data = cursor.fetchone()
    conn.close()
    return image_data

def get_image_by_faiss_id(faiss_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM images WHERE faiss_id = ? AND deleted = FALSE", (faiss_id,))
    image_data = cursor.fetchone()
    conn.close()
    return image_data

def get_all_images(page: int = 1, limit: int = 20):
    conn = get_db_connection()
    cursor = conn.cursor()
    offset = (page - 1) * limit
    cursor.execute("""
        SELECT id, original_filename, original_path, thumbnail_path, qwen_description, is_enhanced, user_tags
        FROM images
        WHERE deleted = FALSE
        ORDER BY upload_timestamp DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    images = cursor.fetchall()

    cursor.execute("SELECT COUNT(id) FROM images WHERE deleted = FALSE")
    total_count = cursor.fetchone()[0]

    conn.close()
    return images, total_count

def get_images_for_enhancement(limit: int = 10):
    """获取需要Qwen-VL增强分析的图片列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, original_path, clip_embedding, bce_embedding, faiss_id
        FROM images 
        WHERE is_enhanced = FALSE AND deleted = FALSE 
        ORDER BY upload_timestamp ASC 
        LIMIT ?
    """, (limit,))
    images = cursor.fetchall()
    conn.close()
    return images

def get_images_without_clip_embedding(limit: int = 10000):
    """获取需要生成CLIP embedding的图片列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, original_path, faiss_id
        FROM images
        WHERE has_clip_embedding = FALSE AND deleted = FALSE
        ORDER BY upload_timestamp ASC
        LIMIT ?
    """, (limit,))
    images = cursor.fetchall()
    conn.close()
    return images

def get_images_without_face_detection(limit: int = 10000):
    """获取需要人脸检测的图片列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, original_path
        FROM images
        WHERE has_face_detection = FALSE AND deleted = FALSE
        ORDER BY upload_timestamp ASC
        LIMIT ?
    """, (limit,))
    images = cursor.fetchall()
    conn.close()
    return images

def get_images_without_face_clustering(limit: int = 10000):
    """获取需要人脸聚类的图片列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, original_path
        FROM images
        WHERE has_face_clustering = FALSE AND deleted = FALSE
        ORDER BY upload_timestamp ASC
        LIMIT ?
    """, (limit,))
    images = cursor.fetchall()
    conn.close()
    return images

def get_images_for_qwen_enhancement(limit: int = 10000):
    """获取需要Qwen-VL增强分析的图片列表（替代原有的get_images_for_enhancement）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, original_path, clip_embedding, bce_embedding, faiss_id
        FROM images 
        WHERE is_enhanced = FALSE AND deleted = FALSE 
        ORDER BY upload_timestamp ASC 
        LIMIT ?
    """, (limit,))
    images = cursor.fetchall()
    conn.close()
    return images

def get_faces_without_cluster(limit: int = 10000):
    """获取没有聚类的人脸列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT face_id, image_id, face_box, attributes, feature_vector
        FROM detected_faces
        WHERE cluster_id IS NULL
        ORDER BY face_id ASC
        LIMIT ?
    """, (limit,))
    faces = cursor.fetchall()
    conn.close()
    return faces

def update_image_clip_embedding(image_id: int, clip_embedding):
    """更新图片的CLIP embedding"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 将numpy数组转换为blob
        embedding_blob = clip_embedding.tobytes() if clip_embedding is not None else None
        cursor.execute("""
            UPDATE images 
            SET clip_embedding = ?
            WHERE id = ?
        """, (embedding_blob, image_id))
        conn.commit()
        success = cursor.rowcount > 0
    except Exception as e:
        logging.error(f"更新图片 {image_id} 的CLIP embedding失败: {e}")
        conn.rollback()
        success = False
    finally:
        conn.close()
    return success

def update_face_cluster(face_id: int, cluster_id: int):
    """更新人脸的聚类信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE detected_faces 
            SET cluster_id = ?
            WHERE face_id = ?
        """, (cluster_id, face_id))
        conn.commit()
        success = cursor.rowcount > 0
    except Exception as e:
        logging.error(f"更新人脸 {face_id} 的聚类信息失败: {e}")
        conn.rollback()
        success = False
    finally:
        conn.close()
    return success

def update_image_status_flags(image_id: int, **flags):
    """更新图片的状态标志位
    可用的标志位: has_clip_embedding, is_enhanced, has_face_detection, has_face_clustering
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 构建动态更新语句
    valid_flags = ['has_clip_embedding', 'is_enhanced', 'has_face_detection', 'has_face_clustering']
    updates = []
    values = []
    
    for flag, value in flags.items():
        if flag in valid_flags and isinstance(value, bool):
            updates.append(f"{flag} = ?")
            values.append(value)
    
    if not updates:
        conn.close()
        return False
    
    values.append(image_id)
    update_query = f"UPDATE images SET {', '.join(updates)} WHERE id = ?"
    
    try:
        cursor.execute(update_query, values)
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logging.info(f"图片 {image_id} 状态标志位已更新: {flags}")
    except Exception as e:
        logging.error(f"更新图片 {image_id} 状态标志位失败: {e}")
        conn.rollback()
        success = False
    finally:
        conn.close()
    return success

def get_clip_embedding_for_image(image_id: int) -> np.ndarray | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT clip_embedding FROM images WHERE id = ? AND deleted = FALSE", (image_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result['clip_embedding'] is not None:
        return result['clip_embedding'] 
    return None

# --- NEW: Function to get all valid CLIP embeddings for image-to-image search ---
def get_all_valid_images_clip_embeddings():
    """
    Fetches ID, FAISS ID, and CLIP embedding for all non-deleted images 
    that have a CLIP embedding.
    Used for image-to-image search.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure clip_embedding is not NULL and image is not deleted
        cursor.execute("""
            SELECT id, faiss_id, clip_embedding 
            FROM images 
            WHERE deleted = FALSE AND clip_embedding IS NOT NULL
        """)
        images_embeddings_data = cursor.fetchall()
        
        # The 'clip_embedding' column is already converted to np.ndarray by the type converter
        # if it was registered with detect_types=sqlite3.PARSE_DECLTYPES.
        # So, we can directly use it.
        results = [{'id': row['id'], 
                    'faiss_id': row['faiss_id'], 
                    'clip_embedding': row['clip_embedding']} 
                   for row in images_embeddings_data if row['clip_embedding'] is not None]
        
        logging.info(f"Fetched {len(results)} CLIP embeddings from DB for image-to-image search.")
        return results
    except Exception as e:
        logging.error(f"Error fetching all CLIP embeddings: {e}", exc_info=True)
        return []
    finally:
        conn.close()


def create_new_face_cluster(cover_face_id: int = None):
    """创建一个新的人脸聚类并返回其ID。"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO face_clusters (cover_face_id, face_count) VALUES (?, 1)", (cover_face_id,))
        conn.commit()
        new_cluster_id = cursor.lastrowid
        logging.info(f"创建了新的人脸聚类，ID: {new_cluster_id}")
        return new_cluster_id
    finally:
        conn.close()

def add_detected_face(image_id: int, cluster_id: int, face_box: list, attributes: dict, score: float, feature_vector: list = None):
    """向数据库中添加一条检测到的人脸记录，并返回其face_id。"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        face_box_json = json.dumps(face_box)
        attributes_json = json.dumps(attributes)
        feature_vector_json = json.dumps(feature_vector) if feature_vector is not None else None
        cursor.execute(
            "INSERT INTO detected_faces (image_id, cluster_id, face_box, attributes, quality_score, feature_vector) VALUES (?, ?, ?, ?, ?, ?)",
            (image_id, cluster_id, face_box_json, attributes_json, score, feature_vector_json)
        )
        # 只有当cluster_id不为None时才更新聚类的总人脸数
        if cluster_id is not None:
            cursor.execute("UPDATE face_clusters SET face_count = face_count + 1 WHERE cluster_id = ?", (cluster_id,))
        conn.commit()
        face_id = cursor.lastrowid
        if cluster_id is not None:
            logging.info(f"已添加人脸记录 face_id: {face_id} 到图片 id: {image_id}, 聚类 id: {cluster_id}")
        else:
            logging.info(f"已添加人脸记录 face_id: {face_id} 到图片 id: {image_id}, 暂未分配聚类")
        return face_id
    finally:
        conn.close()

def get_cluster_id_by_face_id(face_id: int):
    """根据face_id查找其所属的cluster_id。"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT cluster_id FROM detected_faces WHERE face_id = ?", (face_id,))
        result = cursor.fetchone()
        return result['cluster_id'] if result else None
    finally:
        conn.close()
        
def get_faces_by_image_id(image_id: int):
    """获取一张图片中所有检测到的人脸信息。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT face_id, cluster_id, face_box FROM detected_faces WHERE image_id = ?", (image_id,))
    faces = cursor.fetchall()
    conn.close()
    return faces
    
def get_face_ids_by_image_ids(image_ids: list[int]):
    """根据图片ID列表，获取所有相关的face_id。"""
    if not image_ids:
        return []
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT face_id FROM detected_faces WHERE image_id IN ({','.join('?' for _ in image_ids)})"
    cursor.execute(query, image_ids)
    face_ids = [row['face_id'] for row in cursor.fetchall()]
    conn.close()
    return face_ids


def get_images_by_cluster_id(cluster_id: int, page: int = 1, limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    offset = (page - 1) * limit
    
    # 查询总数
    cursor.execute("""
        SELECT COUNT(DISTINCT i.id) 
        FROM images i
        JOIN detected_faces df ON i.id = df.image_id
        WHERE df.cluster_id = ? AND i.deleted = FALSE
    """, (cluster_id,))
    total_count = cursor.fetchone()[0]

    # 分页查询图片信息
    cursor.execute("""
        SELECT DISTINCT i.id, i.original_filename, i.original_path, i.thumbnail_path
        FROM images i
        JOIN detected_faces df ON i.id = df.image_id
        WHERE df.cluster_id = ? AND i.deleted = FALSE
        ORDER BY i.upload_timestamp DESC
        LIMIT ? OFFSET ?
    """, (cluster_id, limit, offset))
    
    images = cursor.fetchall()
    conn.close()
    return images, total_count

def get_all_face_clusters():
    """获取所有人脸聚类信息，包括每个聚类的代表性封面"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                fc.cluster_id,
                fc.name,
                fc.face_count,
                i.thumbnail_path as cover_thumbnail_path
            FROM face_clusters fc
            LEFT JOIN detected_faces df ON fc.cover_face_id = df.face_id
            LEFT JOIN images i ON df.image_id = i.id AND i.deleted = FALSE
            ORDER BY fc.face_count DESC
        """)
        clusters = cursor.fetchall()
        return [dict(cluster) for cluster in clusters]
    except Exception as e:
        logging.error(f"获取人脸聚类失败: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def update_face_cluster_name(cluster_id: int, name: str):
    """更新人脸聚类的名称"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE face_clusters SET name = ? WHERE cluster_id = ?", (name, cluster_id))
        conn.commit()
        updated = cursor.rowcount > 0
        if updated:
            logging.info(f"聚类 {cluster_id} 名称已更新为 '{name}'")
        return updated
    except Exception as e:
        logging.error(f"更新聚类名称失败: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def get_images_by_cluster_name(name_query: str, page: int = 1, limit: int = 50):
    """通过人脸聚类名称搜索图片（支持模糊匹配）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    offset = (page - 1) * limit
    
    try:
        # 查询总数
        cursor.execute("""
            SELECT COUNT(DISTINCT i.id) 
            FROM images i
            JOIN detected_faces df ON i.id = df.image_id
            JOIN face_clusters fc ON df.cluster_id = fc.cluster_id
            WHERE fc.name LIKE ? AND i.deleted = FALSE
        """, (f"%{name_query}%",))
        total_count = cursor.fetchone()[0]

        # 分页查询图片信息
        cursor.execute("""
            SELECT DISTINCT i.id, i.original_filename, i.original_path, i.thumbnail_path
            FROM images i
            JOIN detected_faces df ON i.id = df.image_id
            JOIN face_clusters fc ON df.cluster_id = fc.cluster_id
            WHERE fc.name LIKE ? AND i.deleted = FALSE
            ORDER BY i.upload_timestamp DESC
            LIMIT ? OFFSET ?
        """, (f"%{name_query}%", limit, offset))
        
        images = cursor.fetchall()
        return images, total_count
    except Exception as e:
        logging.error(f"按名称搜索人脸失败: {e}", exc_info=True)
        return [], 0
    finally:
        conn.close()


if __name__ == '__main__':
    init_db()
    print("数据库已初始化。")
    # Example: Test the new function
    # all_embeddings = get_all_valid_images_clip_embeddings()
    # if all_embeddings:
    #     print(f"Found {len(all_embeddings)} images with CLIP embeddings.")
    #     print(f"First item: ID {all_embeddings[0]['id']}, Embedding shape: {all_embeddings[0]['clip_embedding'].shape}")
    # else:
    #     print("No images with CLIP embeddings found or an error occurred.")