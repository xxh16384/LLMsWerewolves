set VENV_PATH=..\.venv
REM �������⻷��������·��
call %VENV_PATH%\Scripts\activate

REM �ֶ�����Python������·��
set PATH=%VENV_PATH%\Scripts;%PATH%

REM ����open-webui����
streamlit run webui.py
