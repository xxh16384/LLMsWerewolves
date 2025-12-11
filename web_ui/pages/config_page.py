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
            api_preset = ''
            api_url = ''
            api_key = ''
            api_model = ''
            valided = {"preset":False, "url":False, "key":False, "model":False}
            manage_api_button_down = False
            def update_api_preset(e):
                nonlocal api_preset
                api_preset = e.value
                valided["preset"] = True if api_preset else False
                update_add_preset_button()
            def update_api_url(e):
                nonlocal api_url
                api_url = e.value
                valided["url"] = True if api_url else False
                update_add_preset_button()
            def update_api_key(e):
                nonlocal api_key
                api_key = e.value
                valided["key"] = True if api_key else False
                update_add_preset_button()
            def update_api_model(e):
                nonlocal api_model
                api_model = e.value
                valided["model"] = True if api_model else False
                update_add_preset_button()

            def update_add_preset_button():
                if all(valided.values()):
                    add_preset_button.enable()
                else:
                    add_preset_button.disable()
                add_preset_button.update()
            
            def update_model_next_button():
                if len(game_config["apis"]) != 0:
                    model_management_next_button.enable()
                else:
                    model_management_next_button.disable()
                model_management_next_button.update()

            def update_manage_api_button():
                nonlocal manage_api_button_down
                if len(game_config["apis"]) != 0:
                    manage_api_button.enable()
                    if manage_api_button_down:
                        manage_api_button.text = "确认删除"
                    else:
                        manage_api_button.text = "管理模型"
                else:
                    manage_api_button.disable()
                    manage_api_button_down = False
                    manage_api_button.text = "管理模型"
                manage_api_button.update()

            def update_api_present_table():
                rows = [{"preset":key,"url":value["base_url"],"key":value["api_key"],"model":value["model_name"]} for key, value in game_config["apis"].items()]
                api_present_table.rows = rows if len(rows) > 0 else [{"preset":"我","url":"是","key":"示","model":"例"}]
                api_present_table.update()

            def update_elements():
                update_api_present_table()
                update_manage_api_button()
                update_model_next_button()
                update_api_present_table()
            def manage_api():
                nonlocal manage_api_button_down
                if not manage_api_button_down:
                    api_present_table.selection = "multiple"
                else:
                    # 删除
                    game_config["apis"] = {key:value for key, value in game_config["apis"].items() if key not in [i["preset"] for i in api_present_table.selected]}
                    api_present_table.selection = "none"
                manage_api_button_down = not manage_api_button_down
                update_elements()

            def add_api():
                game_config["apis"][api_preset] = {
                    'base_url': api_url,
                    'api_key': api_key,
                    'model_name': api_model
                }
                update_elements()

            with ui.card().classes('w-full'):
                with ui.row().classes('w-full'):
                    validation = {'真的那么长吗': lambda value: len(value) < 40,"请输入文本":lambda value: len(value) > 0}
                    ui.input(label='预设名称', placeholder='请输入预设名称',
                        on_change=lambda e: update_api_preset(e),validation=validation)
                    ui.input(label='API地址', placeholder='请输入Base url',
                        on_change=lambda e: update_api_url(e),validation=validation)
                    ui.input(label='API密钥', placeholder='请输入API Key',
                        on_change=lambda e: update_api_key(e),validation=validation)
                    ui.input(label='模型名称', placeholder='请输入模型名称',
                        on_change=lambda e: update_api_model(e),validation=validation)

                add_preset_button = ui.button('添加模型', on_click=add_api)
                update_add_preset_button()

            with ui.card().classes('w-full'):
                ui.label('已添加模型：')
                columns = [{"name":"preset",'field':"preset","label": "预设名称"}, {"name":"url",'field':"url", "label": "API地址"}, {"name":"key",'field':"key", "label": "API密钥"}, {"name":"model",'field':"model", "label": "模型名称"}]
                rows = [{"preset":"我","url":"是","key":"示","model":"例"}]
                api_present_table = ui.table(columns=columns, rows=rows, row_key='preset',selection="none").classes('w-full')
                manage_api_button = ui.button('管理模型', on_click=manage_api)
                update_manage_api_button()

            with ui.stepper_navigation():
                model_management_next_button = ui.button('下一步', on_click=stepper.next)
                update_model_next_button()
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


