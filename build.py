#!/usr/bin/env python3
"""
Debug Pet 打包脚本
使用 PyInstaller 将项目打包成可执行文件
"""

import subprocess
import sys
import os
import shutil

def build():
    """执行打包"""
    print("[INFO] 开始打包 Debug Pet...")
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(current_dir, "debug_pet_pyqt.py")
    dist_dir = os.path.join(current_dir, "dist")
    
    # 清理旧构建
    build_dir = os.path.join(current_dir, "build")
    spec_file = os.path.join(current_dir, "debug_pet_pyqt.spec")
    
    for dir_path in [dist_dir, build_dir]:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print("[INFO] 清理旧目录:", dir_path)
    
    if os.path.exists(spec_file):
        os.remove(spec_file)
    
    # PyInstaller 命令参数
    cmd = [
        "C:\\Users\\w0610\\AppData\\Roaming\\Python\\Python312\\Scripts\\pyinstaller.exe",
        "--name", "DebugPet",
        "--windowed",
        "--onefile",
        "--icon=NONE",
        "--add-data", f"{os.path.join(current_dir, 'miaomiao-all-actions')};miaomiao-all-actions",
        "--add-data", f"{os.path.join(current_dir, 'yu.md')};.",
        "--collect-all", "PyQt5",
        "--collect-all", "PIL",
        "--collect-all", "requests",
        "--collect-all", "pyflakes",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        main_script
    ]
    
    print("[INFO] 执行命令:", " ".join(cmd))
    
    try:
        subprocess.check_call(cmd, cwd=current_dir)
        print("[INFO] PyInstaller 打包完成！")
        
        # 复制资源文件到 dist 目录（确保外部资源可用）
        src_miaomiao = os.path.join(current_dir, "miaomiao-all-actions")
        dst_miaomiao = os.path.join(dist_dir, "miaomiao-all-actions")
        if os.path.exists(src_miaomiao) and not os.path.exists(dst_miaomiao):
            shutil.copytree(src_miaomiao, dst_miaomiao)
            print("[INFO] 复制资源: miaomiao-all-actions ->", dst_miaomiao)
        
        src_yu = os.path.join(current_dir, "yu.md")
        dst_yu = os.path.join(dist_dir, "yu.md")
        if os.path.exists(src_yu):
            shutil.copy2(src_yu, dst_yu)
            print("[INFO] 复制资源: yu.md ->", dst_yu)
        
        # 创建示例配置文件
        settings_file = os.path.join(dist_dir, ".debug_pet_settings")
        if not os.path.exists(settings_file):
            with open(settings_file, 'w', encoding='utf-8') as f:
                f.write("# Debug Pet 配置文件\n")
                f.write("# 启用 AI 代码分析（需要设置 USE_AI=true）\n")
                f.write("USE_AI=true\n\n")
                f.write("# AI 服务选择: deepseek 或 glm\n")
                f.write("AI_SERVICE=glm\n\n")
                f.write("# GLM API 密钥（免费）\n")
                f.write("# 获取地址: https://open.bigmodel.cn/\n")
                f.write("GLM_API_KEY=你的GLM_API密钥\n\n")
                f.write("# DeepSeek API 密钥（可选）\n")
                f.write("# DEEPSEEK_API_KEY=你的DeepSeek_API密钥\n")
            print("[INFO] 创建示例配置文件:", settings_file)
        
        exe_path = os.path.join(dist_dir, "DebugPet.exe")
        print("[INFO] 打包完成！")
        print("[INFO] 可执行文件:", exe_path)
        print("[INFO] 请将 dist 目录下的所有文件一起分发")
        
    except subprocess.CalledProcessError as e:
        print("[ERROR] 打包失败:", e)
        sys.exit(1)

if __name__ == "__main__":
    build()
