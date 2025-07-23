@echo off
chcp 65001 >nul
echo [INFO] 启动脚本：自动配置虚拟环境并运行 gradio_app.py

cd /d %~dp0
echo [INFO] 当前目录：%cd%

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未检测到 Python，请先安装 Python 并添加到环境变量！
    pause
    exit /b
)

REM 检查是否存在虚拟环境
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] 未发现虚拟环境，正在创建...
    python -m venv .venv

    if errorlevel 1 (
        echo [ERROR] 创建虚拟环境失败，请手动检查 Python 安装。
        pause
        exit /b
    )

    echo [INFO] 虚拟环境创建成功，正在激活并安装依赖...
    call .venv\Scripts\activate

    if exist requirements.txt (
        echo [INFO] 检测到 requirements.txt，正在安装依赖...
        pip install --upgrade pip
        pip install -r requirements.txt
        if errorlevel 1 (
            echo [ERROR] 安装依赖失败，请检查 requirements.txt。
            pause
            exit /b
        )
    ) else (
        echo [WARNING] 未找到 requirements.txt，跳过依赖安装。
    )
) else (
    echo [INFO] 虚拟环境已存在，直接激活...
    call .venv\Scripts\activate
)

echo [INFO] 正在运行 gradio_app.py...
python gradio_app.py

echo [INFO] 程序执行完毕
pause
