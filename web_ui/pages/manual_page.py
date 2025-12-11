from nicegui import ui
# 引入我们刚才定义的公共模块
from web_ui.common.layout import theme_layout
from web_ui.common.components import section_title,player_chat_card
from web_ui.common.state import game_config
from core.general import PLAYERDIC,PLAYERDIC_REVERSE
import asyncio

@ui.page("/manual")
@theme_layout
def manual_page():
    section_title(str(game_config["config_valid"]))
    player_chat_card("1","我都说了我是狼人了，你还想咋地？"*20)