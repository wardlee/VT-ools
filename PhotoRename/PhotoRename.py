import os
import re
import time
from datetime import datetime
from PIL import Image
import piexif

def get_date_from_exif(file_path):
    """从图片EXIF中获取日期时间"""
    date = ""
    try:
        with Image.open(file_path) as img:
            exif_info = img._getexif()
            if exif_info:
                # 36867: DateTimeOriginal, 306: DateTime
                if 36867 in exif_info:
                    date = exif_info[36867]
                elif 306 in exif_info:
                    date = exif_info[306]
                if date:
                    date = date.replace(":", "").replace(" ", "_")
    except Exception as e:
        pass
    
    return date

def get_date_from_file_time(file_path):
    """从文件修改时间获取日期时间"""
    t = time.localtime(os.path.getmtime(file_path))
    date = time.strftime("%Y%m%d_%H%M%S", t)
    return date

def convert_unix_timestamp_to_datetime(timestamp_ms):
    """将Unix时间戳(毫秒)转换为日期时间格式"""
    try:
        # 将毫秒转换为秒
        timestamp_sec = int(timestamp_ms) / 1000.0
        # 转换为datetime对象
        dt = datetime.fromtimestamp(timestamp_sec)
        # 格式化为需要的格式
        formatted_date = dt.strftime("%Y%m%d_%H%M%S")
        return formatted_date
    except Exception as e:
        return None

def get_standard_name(file_path, original_name):
    """根据文件名和文件信息获取标准文件名"""
    file_ext = os.path.splitext(original_name)[1].lower()
    is_video = file_ext in ['.mp4', '.mov', '.avi', '.mkv']
    type_suffix = "VID" if is_video else "IMG"
    
    # 从文件名提取日期时间
    date_time = None
    
    # DJI文件格式: DJI_20240628_194800_964.jpg
    if original_name.startswith("DJI_"):
        match = re.search(r'DJI_(\d{8})_(\d{6})_', original_name)
        if match:
            date_time = f"{match.group(1)}_{match.group(2)}"
    
    # 手机相机格式: IMG_20240803_132555.jpg 或 VID_20240724_191943.mp4
    elif original_name.startswith(("IMG_", "VID_")):
        match = re.search(r'(?:IMG|VID)_(\d{8})_(\d{6})', original_name)
        if match:
            date_time = f"{match.group(1)}_{match.group(2)}"
    
    # 微信wx_camera格式: wx_camera_1722700184971.jpg
    elif original_name.startswith("wx_camera_"):
        match = re.search(r'wx_camera_(\d+)', original_name)
        if match:
            timestamp = match.group(1)
            date_time = convert_unix_timestamp_to_datetime(timestamp)
    
    # 微信mmexport格式: mmexport1722689229161.jpg
    elif original_name.startswith("mmexport"):
        match = re.search(r'mmexport(\d+)', original_name)
        if match:
            timestamp = match.group(1)
            date_time = convert_unix_timestamp_to_datetime(timestamp)
    
    # 行车记录仪格式: 20231005080622_0057.mp4
    elif re.match(r'^\d{14}_\d+\.\w+$', original_name):
        match = re.search(r'^(\d{8})(\d{6})_', original_name)
        if match:
            date_time = f"{match.group(1)}_{match.group(2)}"
    
    # 截图格式: Screenshot_2023-12-07-10-30-56-752_app...
    elif original_name.startswith("Screenshot_"):
        match = re.search(r'Screenshot_(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})', original_name)
        if match:
            year, month, day, hour, minute, second = match.groups()
            date_time = f"{year}{month}{day}_{hour}{minute}{second}"
    
    # 如果无法从文件名获取日期时间，尝试从EXIF获取
    if not date_time:
        date_time = get_date_from_exif(file_path)
    
    # 如果仍然无法获取，使用文件修改时间
    if not date_time:
        date_time = get_date_from_file_time(file_path)
    
    # 构建标准文件名
    standard_name = f"{date_time}_{type_suffix}{file_ext}"
    
    return standard_name

def generate_rename_scripts(folder_path):
    """生成重命名脚本和还原脚本"""
    # 添加命令行代码页设置，确保中文显示正确
    rename_script = "@echo off\necho 开始重命名文件...\n"
    restore_script = "@echo off\necho 开始还原文件名...\n"
    
    count = 0
    
    # 遍历文件夹中的所有文件
    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.mkv')):
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, folder_path)
                dir_part = os.path.dirname(relative_path)
                
                # 获取标准文件名
                standard_name = get_standard_name(file_path, filename)
                
                # 构建重命名命令
                if dir_part:
                    # 对于子目录中的文件，先切换到该目录
                    cd_command = f'cd /d "{os.path.join(folder_path, dir_part)}"\n'
                    rename_command = f'ren "{filename}" "{standard_name}"'
                    restore_command = f'ren "{standard_name}" "{filename}"'
                    
                    # 添加到重命名脚本（包含切换目录命令）
                    rename_script += cd_command + rename_command + "\n"
                    
                    # 添加到还原脚本（包含切换目录命令）
                    restore_script += cd_command + restore_command + "\n"
                else:
                    # 对于根目录的文件，直接重命名
                    rename_script += f'ren "{filename}" "{standard_name}"\n'
                    restore_script += f'ren "{standard_name}" "{filename}"\n'
                
                count += 1
    
    # 确保脚本最后返回到原始目录
    rename_script += f"cd /d \"{folder_path}\"\n"
    restore_script += f"cd /d \"{folder_path}\"\n"
    
    rename_script += f"echo 完成！共重命名 {count} 个文件。\npause"
    restore_script += f"echo 完成！共还原 {count} 个文件名。\npause"
    
    # 写入批处理脚本文件，使用GBK编码（适用于中文Windows系统）
    with open(os.path.join(folder_path, "重命名为标准格式.bat"), "w", encoding="gbk") as f:
        f.write(rename_script)
    
    with open(os.path.join(folder_path, "还原原始文件名.bat"), "w", encoding="gbk") as f:
        f.write(restore_script)
    
    return count

def main():
    print("文件重命名工具\n")
    folder_path = input("请输入要处理的文件夹路径: ").strip()
    
    if not os.path.isdir(folder_path):
        print("指定的路径不存在或不是文件夹！")
        return
    
    print(f"正在分析文件夹: {folder_path}...")
    try:
        count = generate_rename_scripts(folder_path)
        print(f"\n处理完成！共找到 {count} 个媒体文件。")
        print(f"已在 {folder_path} 生成以下批处理文件:")
        print("1. 重命名为标准格式.bat - 执行此文件将所有文件重命名为标准格式")
        print("2. 还原原始文件名.bat - 执行此文件可还原为原始文件名")
    except Exception as e:
        print(f"处理过程中出错: {e}")
    
    input("\n按Enter键退出...")

if __name__ == "__main__":
    main() 