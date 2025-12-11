from nicegui import ui
from core.general import EMOJIDIC,PLAYERDIC_REVERSE,PLAYERDIC
from web_ui.common.state import game_config

def section_title(text):
    """通用的章节标题"""
    ui.label(text).classes('text-2xl font-bold text-slate-700 mb-4 border-l-4 border-blue-500 pl-2')

def player_state_card(name, role, alive=True):
    """通用的玩家卡片组件"""
    bg_color = 'bg-white' if alive else 'bg-gray-300'
    text_color = 'text-black' if alive else 'text-gray-500'

    with ui.card().classes(f'w-32 {bg_color} shadow-sm w-full'):
        ui.label(name).classes(f'font-bold {text_color}')
        ui.label(role).classes('text-xs text-gray-400')

def player_chat_card(num,content):
    """通用的玩家卡片组件"""
    info = game_config["players_info"].get(num)
    role = None if not info else info.get("role")
    with ui.card().classes('w-full'):
        with ui.column():
            with ui.row():
                ui.label(EMOJIDIC.get(role)).classes('font-bold')
                ui.label(f'玩家{num}：{PLAYERDIC.get(role)}（{None if not info else info.get("preset")}）').classes('text-gray-400')
            ui.label(content)