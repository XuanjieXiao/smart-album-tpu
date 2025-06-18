# 智能相册 (Smart Album) 接口文档

## 📑 API 接口文档

以下是项目后端提供的API接口详细说明。

### 1. 图片上传
* **URL**: `/upload_images`
* **方法**: `POST`
* **请求体**: `multipart/form-data`
  * `files`: 一个或多个图片文件。
* **成功响应 (200)**:
  ```json
  {
    "message": "成功处理 X 张图片，失败 Y 张。",
    "processed_files": [
      {"id": 1, "faiss_id": 1, "filename": "example.jpg", "status": "success"}
    ]
  }
  ```
* **失败响应 (400, 500)**:
  ```json
  {"error": "错误信息"}
  ```

### 2. 文本搜索图片
* **URL**: `/search_images`
* **方法**: `POST`
* **请求体**: `application/json`
  ```json
  {
    "query_text": "蓝色的天空和白云",
    "top_k": 200
  }
  ```
* **成功响应 (200)**:
  ```json
  {
    "query": "蓝色的天空和白云",
    "results": [
      {
        "id": 1,
        "faiss_id": 1,
        "filename": "sky.jpg",
        "thumbnail_url": "/thumbnails/uuid_thumb.jpg",
        "original_url": "/uploads/uuid.jpg",
        "similarity": 0.8765,
        "qwen_description": "图片描...",
        "qwen_keywords": ["天空", "云"],
        "user_tags": ["风景"],
        "is_enhanced": true
      }
    ],
    "search_mode_is_enhanced": true
  }
  ```

### 3. 图像搜索图片
* **URL**: `/search_by_uploaded_image`
* **方法**: `POST`
* **请求体**: `multipart/form-data`
  * `image_query_file`: 一张用作查询的图片文件。
* **成功响应 (200)**: 响应结构与文本搜索类似，但 `similarity` 是纯粹的CLIP图像向量余弦相似度。
  ```json
  {
    "query_filename": "my_cat.jpg",
    "results": [ /* ... */ ],
    "search_mode_is_enhanced": false
  }
  ```

### 4. 获取所有图片（分页）
* **URL**: `/images`
* **方法**: `GET`
* **查询参数**:
  * `page`: 页码 (默认 1)
  * `limit`: 每页数量 (默认 40)
* **成功响应 (200)**:
  ```json
  {
    "images": [
      {
        "id": 1,
        "filename": "example.jpg",
        "thumbnail_url": "/thumbnails/xxx_thumb.jpg",
        "original_url": "/uploads/xxx.jpg",
        "is_enhanced": true,
        "user_tags": ["标签1"]
      }
    ],
    "total_count": 100,
    "page": 1,
    "limit": 40,
    "total_pages": 3
  }
  ```

### 5. 获取单张图片详情
* **URL**: `/image_details/<image_db_id>`
* **方法**: `GET`
* **成功响应 (200)**:
  ```json
  {
    "id": 1,
    "filename": "example.jpg",
    "original_url": "/uploads/xxx.jpg",
    "qwen_description": "图片描述",
    "qwen_keywords": ["关键词1", "关键词2"],
    "user_tags": ["标签1", "标签2"],
    "is_enhanced": true
  }
  ```

### 6. 手动触发图片增强分析
* **URL**: `/enhance_image/<image_db_id>`
* **方法**: `POST`
* **成功响应 (200)**:
  ```json
  {
    "message": "图片 ID X 分析增强成功。",
    "qwen_description": "新生成的图片描述",
    "qwen_keywords": ["新关键词1", "新关键词2"],
    "is_enhanced": true
  }
  ```

### 7. 批量删除图片
* **URL**: `/delete_images_batch`
* **方法**: `POST`
* **请求体**: `application/json`
  ```json
  {"image_ids": [1, 2, 3]}
  ```
* **成功响应 (200)**:
  ```json
  {
    "success": true,
    "message": "成功删除 X 张图片。",
    "failed_ids": []
  }
  ```

### 8. 批量添加用户标签
* **URL**: `/add_user_tags_batch`
* **方法**: `POST`
* **请求体**: `application/json`
  ```json
  {
    "image_ids": [1, 2, 3],
    "user_tags": ["风景", "家庭"]
  }
  ```
* **成功响应 (200)**:
  ```json
  {
    "success": true,
    "message": "成功为 X 张图片添加/更新了用户标签。",
    "failed_ids": []
  }
  ```

### 9. 应用设置管理
* **URL**: `/config/settings`
* **方法**: `GET` (获取当前设置), `POST` (更新设置)
* **请求体 (POST)**: `application/json`
  ```json
  {
    "qwen_vl_analysis_enabled": true,
    "use_enhanced_search": false
  }
  ```
* **响应 (GET/POST)**:
  ```json
  {
    "qwen_vl_analysis_enabled": true,
    "use_enhanced_search": false
  }
  