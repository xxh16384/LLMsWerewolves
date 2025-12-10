from nicegui import ui
# 引入我们刚才定义的公共模块
from web_ui.common.layout import theme_layout
from web_ui.common.components import section_title
from web_ui.common.state import game_config

@ui.page('/')
@theme_layout  # <--- 套用布局
def config_page():
    section_title('游戏初始化设置')
    
    with ui.stepper().props('vertical').classes('w-full') as stepper:
        with ui.step('模型管理'):
            model_name = ''
            def result(e):
                nonlocal model_name
                model_name = e.value
            with ui.row():
                ui.input(label='模型简称', placeholder='请输入模型简称',
                    on_change=lambda e: result(e),
                    validation={'Input too long': lambda value: len(value) < 20})


            with ui.stepper_navigation():
                ui.button('下一步', on_click=stepper.next)
        with ui.step('玩家配置'):
            ui.label('Mix the ingredients')
            with ui.stepper_navigation():
                ui.button('下一步', on_click=stepper.next)
                ui.button('上一步', on_click=stepper.previous).props('flat')
        with ui.step('提示词设置'):
            ui.label('Mix the ingredients')
            with ui.stepper_navigation():
                ui.button('下一步', on_click=stepper.next)
                ui.button('上一步', on_click=stepper.previous).props('flat')
        with ui.step('完成'):
            ui.label('Bake for 20 minutes')
            with ui.stepper_navigation():
                ui.button('完成配置！', on_click=lambda: ui.notify('芜湖~', type='positive'))
                ui.button('上一步', on_click=stepper.previous).props('flat')


