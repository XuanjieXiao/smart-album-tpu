import sqlite3
import os
import sys

# --- 配置 ---
# 确保这个路径指向你的数据库文件
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "data", "smart_album.db")

# --- 迁移函数 ---
def migrate_database_paths():
    """
    连接到数据库，并将 smart_album 表中的绝对路径转换为相对路径。
    例如：/path/to/project/uploads/abc.jpg -> uploads/abc.jpg
    """
    if not os.path.exists(DB_PATH):
        print(f"错误：在 '{DB_PATH}' 未找到数据库文件。")
        sys.exit(1)

    print(f"正在连接到数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    # 使用 Row 工厂可以让我们可以通过列名访问数据
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        print("正在从 'images' 表中读取所有记录...")
        cursor.execute("SELECT id, original_path, thumbnail_path FROM images")
        images = cursor.fetchall()

        if not images:
            print("数据库中没有图片记录，无需迁移。")
            return

        updates_to_perform = []

        for image in images:
            needs_update = False

            # --- 处理原始图片路径 ---
            old_original = image['original_path']
            new_original = old_original

            if old_original and os.path.isabs(old_original):
                # 通过 "uploads/" 标记来分割路径
                parts = old_original.split('uploads/')
                if len(parts) > 1:
                    new_original = 'uploads/' + parts[1]
                    needs_update = True
                    print(f"  [ID: {image['id']}] 原始路径转换: '{old_original}' -> '{new_original}'")

            # --- 处理缩略图路径 ---
            old_thumbnail = image['thumbnail_path']
            new_thumbnail = old_thumbnail

            if old_thumbnail and os.path.isabs(old_thumbnail):
                # 通过 "thumbnails/" 标记来分割路径
                parts = old_thumbnail.split('thumbnails/')
                if len(parts) > 1:
                    new_thumbnail = 'thumbnails/' + parts[1]
                    needs_update = True
                    print(f"  [ID: {image['id']}] 缩略图路径转换: '{old_thumbnail}' -> '{new_thumbnail}'")

            if needs_update:
                # 将需要更新的数据添加到列表中
                updates_to_perform.append((new_original, new_thumbnail, image['id']))

        if not updates_to_perform:
            print("所有路径已经是相对路径或格式正确，无需更新。")
            return

        # --- 批量执行更新 ---
        print(f"\n准备更新 {len(updates_to_perform)} 条记录...")
        cursor.executemany(
            "UPDATE images SET original_path = ?, thumbnail_path = ? WHERE id = ?", 
            updates_to_perform
        )

        # 提交事务
        conn.commit()
        print(f"\n成功！数据库迁移完成。共更新了 {cursor.rowcount} 条记录。")

    except Exception as e:
        print(f"\n迁移过程中发生错误: {e}")
        conn.rollback() # 如果出错，回滚所有更改
    finally:
        conn.close()
        print("数据库连接已关闭。")


# --- 运行主程序 ---
if __name__ == '__main__':
    print("="*50)
    print("     智能相册数据库路径迁移工具")
    print("="*50)
    print("本工具会将数据库中的绝对文件路径转换为相对路径。")

    # ！！！关键步骤：获取用户确认！！！
    # 注意：在Python 3中，input返回的是字符串
    response = input(f"你是否已经备份了 '{DB_PATH}' 文件？(yes/no): ").lower().strip()

    if response == 'yes':
        migrate_database_paths()
    else:
        print("\n操作取消。请先备份数据库文件再运行此脚本。")