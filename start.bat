@echo off
REM 自动激活虚拟环境并运行 gradio_app.py
cd /d %~dp0
call .venv\Scripts\activate
python gradio_app.py
pause 