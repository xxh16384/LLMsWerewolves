from nicegui import ui
from functools import wraps
def menu_link(text, target):
    """侧边栏的一个菜单项"""
    # 获取当前路径，如果是当前页，加深背景色
    # 注意：这里做简单的跳转
    ui.link(text, target).classes('w-full block px-4 py-3 hover:bg-slate-700 text-gray-200 no-underline border-b border-slate-700')

def theme_layout(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 1. 先创建左侧抽屉实例并保存到变量
        left_drawer = ui.left_drawer(value=False).classes('bg-slate-800 text-white')

        # 2. 顶部 Header - 现在可以使用正确的抽屉实例
        with ui.header().classes('bg-slate-900 text-white h-16 items-center shadow-md'):
            # 直接传递方法引用，而不是lambda表达式
            ui.button(icon='menu', on_click=left_drawer.toggle).props('flat color=white')
            ui.label('🐺 AI 狼人杀控制台').classes('text-xl font-bold ml-4 tracking-wider')

        # 3. 配置左侧抽屉内容
        with left_drawer:
            ui.label('导航').classes('px-4 py-4 text-xs text-gray-400 uppercase font-bold')
            menu_link('⚙️ 游戏配置', '/')
            menu_link('🙋‍♂️ 手动模式', '/manual')

        # 4. 页面主要内容区
        with ui.column().classes('w-full p-6 bg-gray-50 min-h-screen'):
            func(*args, **kwargs)

    return wrapper