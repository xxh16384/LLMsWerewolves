from nicegui import ui
from functools import wraps
def menu_link(text, target):
    """侧边栏的一个菜单项"""
    # 获取当前路径，如果是当前页，加深背景色
    # 注意：这里做简单的跳转
    ui.link(text, target).classes('w-full block px-4 py-3 hover:bg-slate-700 text-gray-200 no-underline border-b border-slate-700')

def theme_layout(func):
    @wraps(func)  # <--- 2. 加上这一行！这非常关键
    def wrapper(*args, **kwargs):
        # 顶部 Header
        with ui.header().classes('bg-slate-900 text-white h-16 items-center shadow-md'):
            ui.button(icon='menu', on_click=lambda: ui.left_drawer.toggle()).props('flat color=white')
            ui.label('🐺 AI 狼人杀控制台').classes('text-xl font-bold ml-4 tracking-wider')

        # 左侧 Sidebar
        with ui.left_drawer(value=True).classes('bg-slate-800 text-white'):
            # ... 你的侧边栏代码 ...
            ui.label('导航').classes('px-4 py-4 text-xs text-gray-400 uppercase font-bold')
            # 这里的 menu_link 调用略...

        # 页面主要内容区
        with ui.column().classes('w-full p-6 bg-gray-50 min-h-screen'):
            # 执行原函数
            func(*args, **kwargs)
            
    return wrapper