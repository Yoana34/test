import subprocess
import sys
import os

def main():
    """启动Streamlit GUI应用"""
    print("正在启动自然语言数据库查询系统...")
    print("请确保MCP服务器正在运行 (python main.py)")
    print("浏览器将自动打开GUI界面")
    print("-" * 50)
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建gui.py的完整路径
    gui_path = os.path.join(current_dir, "gui.py")
    
    try:
        # 启动Streamlit应用
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", gui_path,
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"启动失败: {e}")
        print("请确保已安装Streamlit: pip install streamlit")
    except KeyboardInterrupt:
        print("\n 应用已停止")

if __name__ == "__main__":
    main() 