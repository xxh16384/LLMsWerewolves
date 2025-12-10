from nicegui import ui

# --- 全局配置状态 (简单的内存存储) ---
# 在实际项目中，这里可以换成读取你的 config/json 文件
game_settings = {
    "player_count": 6,
    "has_witch": True,
    "has_seer": True,
    "speed": 1.0
}

# --- 通用布局装饰器 ---
def main_layout(func):
    """
    这是一个装饰器，或者是 Context Manager 的一种变体。
    它可以让每个页面都自动拥有 Header 和 Sidebar。
    """
    def wrapper(*args, **kwargs):
        # 1. 统一的顶部栏
        with ui.header().classes('bg-slate-800 items-center'):
            ui.button(on_click=lambda: ui.left_drawer.toggle(), icon='menu').props('flat color=white')
            ui.label('🐺 AI 狼人杀工作台').classes('text-xl font-bold ml-4')

        # 2. 统一的侧边栏 (导航菜单)
        with ui.left_drawer(value=True).classes('bg-slate-100') as drawer:
            ui.label('菜单').classes('text-gray-500 text-sm font-bold px-4 py-2')

            # 导航链接
            # 注意：这里直接跳转到对应的 URL
            ui.link('⚙️ 游戏配置', '/').classes('w-full block px-4 py-2 hover:bg-gray-200 text-black no-underline')
            #ui.link('🤖 自动对战', '/auto').classes('w-full block px-4 py-2 hover:bg-gray-200 text-black no-underline')
            #ui.link('🙋‍♂️ 手动模式', '/manual').classes('w-full block px-4 py-2 hover:bg-gray-200 text-black no-underline')

        # 3. 渲染具体的页面内容 (中间部分)
        with ui.column().classes('w-full p-4'):
            func(*args, **kwargs)

    return wrapper