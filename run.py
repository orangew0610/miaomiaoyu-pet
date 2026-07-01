#!/usr/bin/env python3
"""
Debug Pet 启动器
自动检测并安装依赖，然后启动主程序
"""

import subprocess
import sys
import os

def install_requirements():
    """安装依赖"""
    print("📦 正在安装依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])
        print("✅ 依赖安装完成！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def main():
    # 先安装依赖
    if not install_requirements():
        sys.exit(1)

    # 启动主程序
    print("🚀 启动 Debug Pet...")
    os.system("python debug_pet_pyqt.py")

if __name__ == "__main__":
    main()
