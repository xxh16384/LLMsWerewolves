# run_web.py
from nicegui import ui

# 核心：必须导入这些模块，否则路由不会注册
from web_ui.pages import config_page
from web_ui.pages import manual_page

if __name__ in {"__main__", "__mp_main__"}:
    # 全局样式调整（可选）
    ui.run(
        title="AI狼人杀！",
        port=8080,
        favicon="🐺",
        language="zh-CN"
    )