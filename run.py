import os
import sys
import subprocess
import time
import signal
from pathlib import Path

# Reconfigure stdout/stderr to utf-8 to prevent GBK UnicodeEncodeError on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

def check_and_create_venv():
    venv_dir = BASE_DIR / ".venv"
    pip_exe = venv_dir / "Scripts" / "pip.exe"
    python_exe = venv_dir / "Scripts" / "python.exe"

    if not venv_dir.exists():
        print("[-] 正在为您创建 Python 虚拟环境 (Virtual Environment)...")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
            print("[+] 虚拟环境创建成功。")
        except subprocess.CalledProcessError as e:
            print(f"[x] 创建虚拟环境失败: {e}")
            sys.exit(1)

    # Check if dependencies are installed by checking package requirements
    # Let's perform a pip install to ensure all requirements are satisfied
    print("[-] 正在检查并安装依赖项 (pip install -r requirements.txt)...")
    try:
        # Run pip upgrade using python -m pip to avoid file locking on Windows
        subprocess.run([
            str(python_exe), "-m", "pip", "install", "--upgrade", "pip"
        ], check=True, stdout=subprocess.DEVNULL)
        
        subprocess.run([
            str(pip_exe), "install", "-r", str(BASE_DIR / "requirements.txt")
        ], check=True)
        print("[+] 依赖安装/检查完成。")
    except subprocess.CalledProcessError as e:
        print(f"[x] 安装依赖失败，请检查网络或配置: {e}")
        sys.exit(1)

    return python_exe, venv_dir

def create_default_dotenv():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        print("[-] 正在创建默认的 .env 配置文件...")
        default_env = (
            "LLM_PROVIDER=gemini\n"
            "GEMINI_API_KEY=\n"
            "OPENAI_API_KEY=\n"
            "EMAIL_IMAP_SERVER=imap.gmail.com\n"
            "EMAIL_ADDRESS=\n"
            "EMAIL_PASSWORD=\n"
            "EMAIL_SYNC_DAYS=14\n"
            "EMAIL_MAX_FETCH=50\n"
        )
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(default_env)
        print("[+] .env 配置文件创建完成。您可以在 Streamlit 界面或直接在文件中编辑配置。")

def main():
    print("====================================================")
    print("🚀 欢迎启动 JobButler Agent (智能求职管家)")
    print("====================================================")

    create_default_dotenv()
    python_exe, venv_dir = check_and_create_venv()

    # Define command executables in the venv
    uvicorn_exe = venv_dir / "Scripts" / "uvicorn.exe"
    streamlit_exe = venv_dir / "Scripts" / "streamlit.exe"

    if not uvicorn_exe.exists() or not streamlit_exe.exists():
        print("[x] 未能在虚拟环境中找到 uvicorn 或 streamlit。尝试重新安装依赖。")
        sys.exit(1)

    # Configure environment to force UTF-8 output encoding for child Python processes
    sub_env = os.environ.copy()
    sub_env["PYTHONIOENCODING"] = "utf-8"

    print("\n[-] 正在启动 FastAPI 后端服务器 (Port 8000)...")
    # Run uvicorn backend/app/main.py -> backend.app.main:app
    backend_proc = subprocess.Popen([
        str(uvicorn_exe), "backend.app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ], cwd=str(BASE_DIR), env=sub_env)

    # Give backend 2 seconds to bind port
    time.sleep(2.0)

    print("[-] 正在启动 Streamlit 前端服务 (Port 8501)...")
    # Run streamlit run frontend/app.py
    frontend_proc = subprocess.Popen([
        str(streamlit_exe), "run", "frontend/app.py",
        "--server.port", "8501",
        "--server.headless", "true"
    ], cwd=str(BASE_DIR), env=sub_env)

    print("\n====================================================")
    print("[🎉 运行成功] 系统已就绪，请使用浏览器访问：")
    print("➡️   前端页面: http://localhost:8501")
    print("➡️   后端 API: http://localhost:8000")
    print("\n按下 Ctrl + C 即可安全退出管家系统。")
    print("====================================================")

    # Listen to keyboard interrupt
    try:
        while True:
            # Check if any process has exited
            if backend_proc.poll() is not None:
                print("[x] 后端服务异常退出！")
                break
            if frontend_proc.poll() is not None:
                print("[x] 前端服务异常退出！")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[-] 收到退出指令，正在关闭所有管家服务...")
    finally:
        # Graceful shutdown of subprocesses
        backend_proc.terminate()
        frontend_proc.terminate()
        try:
            backend_proc.wait(timeout=2)
            frontend_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            backend_proc.kill()
            frontend_proc.kill()
        print("[+] 所有管家服务已安全关闭。")

if __name__ == "__main__":
    main()
