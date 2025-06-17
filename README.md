# 智能相册 (Smart Album) - (基于 Sophgo TPU、Chinese-CLIP 与 Qwen-VL)

本项目是一个功能完备、基于 Flask 的智能相册 Web 应用，专为在 **Sophgo TPU** 硬件上高效运行而设计。它允许用户上传图片，并通过两种强大的方式进行智能检索：**中文文本描述搜图**和**以图搜图**。

系统深度整合了硬件加速的 AI 模型，利用 **Chinese-CLIP** 生成高质量的图文特征向量，**BCE (BERT-based Chinese Embedding)** 模型增强文本理解能力，并通过 **FAISS** 实现海量数据的毫秒级向量检索。此外，项目还集成了 **Qwen-VL** 大语言模型的云服务，能够对图片进行深入分析，自动生成详细的描述和精准的关键词，从而极大地提升了“增强搜索”模式下的检索精度和用户体验。所有图片元数据和 AI 分析结果都通过 **SQLite3** 数据库进行持久化存储和管理。

## ✨ 功能特点 (Features)

* **图片上传与管理 (Image Upload & Management)**:
  * 支持单张或批量图片上传。
  * 自动为上传的图片生成缩略图，优化加载速度。
  * 支持对单张或多选图片进行永久删除。
  * 支持为单张或多选图片批量添加自定义标签。

* **智能搜索 (Intelligent Search)**:
  * **文本搜图**: 输入中文自然语言描述，系统能理解语义并找出最相关的图片。
  * **图像搜图**: 上传一张图片作为查询，系统会找出图片库中所有视觉上相似的图片。
  * **增强搜索**: 可在控制面板中开启/关闭的混合检索模式。开启后，搜索时会融合图片的视觉特征（CLIP）和其AI生成描述的文本特征（BCE），提供更精准、更符合人类直觉的搜索结果。

* **AI图片分析 (AI-Powered Analysis)**:
  * 通过集成 **Qwen-VL** 模型，可在图片上传时自动或在之后手动为图片生成详细的中文描述和关键词标签。
  * AI分析结果不仅方便用户理解图片内容，还会被“增强搜索”模式利用以提升检索质量。

* **用户界面 (User Interface)**:
  * **主页**: 简洁的界面，集成了文本和图像搜索功能，并以无限滚动的瀑布流形式展示整个图片库。
  * **控制面板**: 提供一个独立的页面，用于管理应用的核心设置，如是否自动进行AI分析、是否启用增强搜索等。
  * **图片详情**: 双击任意图片可打开一个模态框，清晰展示高清大图、文件名、AI生成的描述与关键词、用户自定义标签以及搜索时的相似度分数。
  * **批量操作**: 用户可以方便地点击选择多张图片，导航栏上会动态显示“删除选中”和“标记选中”按钮，以进行高效的批量管理。

## 🛠️ 技术栈 (Technology Stack)

* **后端 (Backend)**: Python, Flask
* **AI 模型 (AI Models)**:
  * **图文特征提取 (Image-Text Features)**: **Chinese-CLIP (ViT-H-14)**，使用为 Sophgo TPU 优化的 `.bmodel` 格式，通过 `sophon.sail` API 进行硬件加速推理。
  * **文本向量化 (Text Vectorization)**: **BCE (BERT-based Chinese Embedding)** 模型 (`shibing624/text2vec-base-chinese`)，同样使用 `.bmodel` 格式在 TPU 上运行。
  * **图片视觉语言分析 (Vision-Language Analysis)**: **Qwen-VL**，通过 `qwen_service.py` 调用云端 API 实现。
* **向量数据库 (Vector Database)**: FAISS (CPU版本)
* **元数据数据库 (Metadata DB)**: SQLite3
* **前端 (Frontend)**: 原生 HTML, CSS, JavaScript

## 📋 项目结构 (Project Structure)

```
smart-album-tpu/
├── app.py                     # 主 Flask 应用，包含所有API路由和核心逻辑
├── bce_embedding/             # BCE 文本向量化模块 (基于sophon.sail)
│   ├── __init__.py
│   └── bce_embedding.py
├── clip/                      # Chinese-CLIP 图文特征提取模块 (基于sophon.sail)
│   ├── __init__.py
│   ├── clip.py
│   └── ...
├── database_utils.py          # SQLite3 数据库辅助函数
├── faiss_utils.py             # FAISS 向量索引管理
├── qwen_service.py            # Qwen-VL 图片分析服务 (调用云API)
├── requirements.txt           # Python 依赖包
├── static/                    # 前端静态文件 (CSS, JS, images)
├── templates/                 # HTML 模板 (index.html, controls.html)
├── models/                    # 存放编译好的 .bmodel 文件和 tokenizer 配置
│   ├── BM1684X/               # 示例硬件平台目录
│   │   ├── cn_clip_image_...bmodel
│   │   ├── cn_clip_text_...bmodel
│   │   └── text2vec_base_...bmodel
│   └── shibing624/            # Tokenizer 配置文件目录
├── data/                      # 运行时生成的数据文件
│   ├── smart_album.db         # SQLite 数据库文件
│   ├── album_faiss.index      # FAISS 索引文件
│   └── app_config.json        # 应用配置文件
├── uploads/                   # 用户上传的原始图片 (运行时创建)
└── thumbnails/                # 生成的缩略图 (运行时创建)
```

## 🚀 环境准备与运行

### 1. 硬件与软件环境
* **硬件**: 本项目专为 **Sophgo TPU** (如 BM1684X 系列) 设计，其性能依赖于 TPU 的硬件加速能力。
* **Python**: 建议使用 Python 3.9 或更高版本。
* **Sophon SDK**: 请确保您已在您的硬件平台上正确安装了 Sophgo SDK，并配置好了 `sophon.sail` Python 库的运行环境。

### 2. 安装依赖
克隆项目后，建议在 Python 虚拟环境中安装所有必需的依赖包。
```bash
# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 模型文件准备
* 本项目需要使用为 Sophgo TPU 编译的 `.bmodel` 文件。请将您的 `cn_clip` (image 和 text) 和 `bce` 模型的 `.bmodel` 文件放置在 `models/BM1684X/` 目录下（或根据您的硬件修改 `app.py` 中的启动参数路径）。
* 确保 `models/shibing624/text2vec-base-chinese` 目录中包含 BCE 模型所需的 `tokenizer` 相关配置文件。

### 4. Qwen-VL API 配置
* 打开 `qwen_service.py` 文件。
* 在文件顶部找到并修改 `QWEN_API_KEY` 和 `QWEN_BASE_URL` 为您的 Qwen-VL 服务凭证。
* **安全提示**: 强烈建议通过环境变量 (`export QWEN_API_KEY="your_key"`) 来设置 API 密钥，而不是直接硬编码在代码中。

### 5. 运行项目
在项目根目录下，使用以下命令启动后端服务。您必须通过命令行参数指定模型文件的路径和要使用的 TPU 设备 ID。
```bash
python app.py \
  --image_model './models/BM1684X/cn_clip_image_vit_h_14_bm1684x_f16_1b.bmodel' \
  --text_model './models/BM1684X/cn_clip_text_vit_h_14_bm1684x_f16_1b.bmodel' \
  --bce_model './models/BM1684X/text2vec_base_chinese_bm1684x_f16_1b.bmodel' \
  --dev_id 0
```
* `--dev_id`: 指定要使用的 TPU 设备 ID (例如，0, 1, ...)。

服务默认会在 `http://0.0.0.0:5000` 启动。在浏览器中打开 `http://localhost:5000` 即可开始使用。

---

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
  