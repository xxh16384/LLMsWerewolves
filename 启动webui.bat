set VENV_PATH=E:\���Դ�ģ��\.venv
REM �������⻷��������·��
call %VENV_PATH%\Scripts\activate

REM �ֶ�����Python������·��
set PATH=%VENV_PATH%\Scripts;%PATH%

REM ����open-webui����
streamlit run E:\���Դ�ģ��\LLMsWerewolves\webui.py
