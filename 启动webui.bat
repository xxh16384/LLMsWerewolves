set VENV_PATH=E:\试试大模型\.venv
REM 激活虚拟环境并设置路径
call %VENV_PATH%\Scripts\activate

REM 手动设置Python解释器路径
set PATH=%VENV_PATH%\Scripts;%PATH%

REM 启动open-webui服务
streamlit run E:\试试大模型\LLMsWerewolves\webui.py
