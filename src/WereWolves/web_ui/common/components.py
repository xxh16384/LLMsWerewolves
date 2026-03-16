from nicegui import ui

def section_title(text):
    """通用的章节标题"""
    ui.label(text).classes('text-2xl font-bold text-slate-700 mb-4 border-l-4 border-blue-500 pl-2')

def player_card(name, role, alive=True):
    """通用的玩家卡片组件"""
    bg_color = 'bg-white' if alive else 'bg-gray-300'
    text_color = 'text-black' if alive else 'text-gray-500'
    
    with ui.card().classes(f'w-32 {bg_color} shadow-sm'):
        ui.label(name).classes(f'font-bold {text_color}')
        ui.label(role).classes('text-xs text-gray-400')