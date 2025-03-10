import streamlit as st
from main import Game, Context, find_max_key, read_json
import time
from threading import Thread, Lock, Event
from queue import Queue
import json

# 角色颜色配置
ROLE_COLORS = {
    "上帝": "#FFFFFF",    # 白色
    "werewolf": "#FF6B6B",  # 红色
    "villager": "#4ECDC4",  # 青色
    "witch": "#96CEB4",     # 绿色
    "seer": "#45B7D1"       # 蓝色
}

player_role_to_chinese = {
    "werewolf": "狼人",
    "villager": "村民",
    "witch": "女巫",
    "seer": "预言家",
    "上帝": "上帝",
    "未知": "未知"
}

ROLE_ICONS = {
    "werewolf": "🐺",
    "villager": "👨🌾",
    "witch": "🧙♀",
    "seer": "🔮",
    "上帝":"👑",
    "未知":"❓"
}

stander_roles = ["werewolf", "villager", "witch", "seer"]

def init_session_state():
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'config'
    if 'game' not in st.session_state:
        st.session_state.game = None
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    if 'game_lock' not in st.session_state:
        st.session_state.game_lock = Lock()
    if 'phase_thread' not in st.session_state:
        st.session_state.phase_thread = None
    if 'phase_progress' not in st.session_state:
        st.session_state.phase_progress = None
    if 'models' not in st.session_state:
        st.session_state.models = [{
                            "name": "QwQ-32B试用版（可能卡顿）",
                            "api_key": "sk-W0rpStc95T7JVYVwDYc29IyirjtpPPby6SozFMQr17m8KWeo",
                            "base_url": "https://api.suanli.cn/v1",
                            "model_name": "free:QwQ-32B"
                        }]
    if 'players' not in st.session_state:
        st.session_state.players = []
    if 'player_num' not in st.session_state:
        st.session_state.player_num = 8
    if 'msg_progress' not in st.session_state:
        st.session_state.msg_progress = None
    if 'msg_queue' not in st.session_state:
        st.session_state.msg_queue = Queue()
    if 'instructions' not in st.session_state:
        try:
            st.session_state.instructions = read_json("./config/default_instructions.json")
        except:
            st.session_state.instructions = {
                "general": "",
                "werewolf": "",
                "villager": "",
                "witch": "",
                "seer": ""
            }
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 0

# 配置页面
def config_page():
    st.set_page_config(page_title="游戏配置🤔", page_icon="🎮", layout="wide", initial_sidebar_state="expanded", menu_items={"About":"https://github.com/xxh16384/LLMsWerewolves"})
    with st.sidebar:
        st.title("🎮 快速配置")
        st.divider()
        st.markdown("""
        **游戏规则提示**

        ▸ 最少需要4名玩家

        ▸ 需要至少1个狼人角色

        ▸ 每个玩家必须分配模型
        """)
        st.divider()
        game_name = st.text_input("输入游戏名称", "狼人杀游戏1")

        # 配置文件上传区域
        with st.expander("⚡ 快速加载配置", expanded=True):
            files = {
                "instructions": st.file_uploader("提示词配置(instructions.json)", type=["json"]),
                "player_info": st.file_uploader("玩家配置(player_info.json)", type=["json"]),
                "apis": st.file_uploader("API配置(apis.json)", type=["json"])
            }

            load_cols = st.columns([2,1])
            with load_cols[0]:
                if st.button("📥 加载配置到表单", help="将上传的配置合并到当前表单", use_container_width=True):
                    try:
                        # 模型配置加载
                        if files["apis"]:
                            apis_config = json.load(files["apis"])
                            existing_names = [m["name"] for m in st.session_state.models]

                            # 智能合并模型配置
                            for name, config in apis_config.items():
                                if name not in existing_names:
                                    st.session_state.models.append({
                                        "name": name,
                                        "api_key": config["api_key"],
                                        "base_url": config.get("base_url", "https://api.openai.com/v1"),
                                        "model_name": config["model_name"]
                                    })

                        # 修改玩家配置加载部分
                        if files["player_info"]:
                            players_config = json.load(files["player_info"])
                            new_players = []

                            # 提取数字键并排序
                            player_keys = [k for k in players_config.keys() if k.isdigit()]
                            player_keys = sorted(player_keys, key=lambda x: int(x))

                            # 遍历排序后的玩家键
                            for key in player_keys:
                                player_data = players_config[key]
                                if isinstance(player_data, dict):  # 确保是玩家数据
                                    new_players.append({
                                        "role": player_data.get("role", "villager"),
                                        "model": player_data.get("model", "")
                                    })

                            # 验证玩家数量
                            if len(new_players) < 4:
                                st.error("玩家数量不能少于4个")
                            else:
                                st.session_state.players = new_players
                                st.session_state.player_num = len(new_players)

                        # 提示词加载
                        if files["instructions"]:
                            try:
                                st.session_state.instructions = json.load(files["instructions"])
                            except Exception as e:
                                st.error(f"提示词解析失败: {str(e)}")

                        st.success("配置已加载到当前表单！")
                        success_msg = "成功加载了"
                        if files["apis"]: success_msg += " API配置"
                        if files["player_info"]: success_msg += " 玩家配置"
                        if files["instructions"]: success_msg += " 提示词配置"
                        if success_msg == "成功加载了":
                            success_msg = "未加载"
                        st.session_state.alert_message = success_msg  # 设置弹窗消息
                        st.session_state.current_step = 3  # 跳转到最后一步
                        st.rerun()


                    except json.JSONDecodeError:
                        st.error("配置文件格式错误，请检查JSON格式")
                    except Exception as e:
                        st.error(f"配置加载失败: {str(e)}")

            with load_cols[1]:
                if st.button("🔄 重置表单", help="清空所有配置", type="secondary", use_container_width=True):
                    st.session_state.models = []
                    st.session_state.players = []
                    st.session_state.instructions = read_json("./config/default_instructions.json")
                    st.session_state.current_step = 0
                    st.rerun()

        # 配置备份区域
        with st.expander("💾 备份和导入配置", expanded=False):
            st.download_button(
                label="导出完整配置",
                data=json.dumps({
                    "apis": {m["name"]: m for m in st.session_state.models},
                    "players": st.session_state.players,
                    "instructions": st.session_state.instructions
                }, ensure_ascii=False, indent=2),
                file_name="werewolf_config.json",
                mime="application/json",
                use_container_width=True
            )
            # 新增导入配置上传器
            imported_config = st.file_uploader("上传备份配置", type=["json"], key="import_config")

            if imported_config and st.button("导入配置", use_container_width=True):
                try:
                    config_data = json.load(imported_config)
                    # 校验配置结构
                    required_keys = ["apis", "players", "instructions"]
                    if not all(k in config_data for k in required_keys):
                        st.error("配置文件格式不完整")
                    else:
                        # 合并模型配置（防重复）
                        existing_model_names = [m["name"] for m in st.session_state.models]
                        for name, config in config_data["apis"].items():
                            if name not in existing_model_names:
                                st.session_state.models.append(config)

                        # 更新玩家配置
                        if len(config_data["players"]) >= 4:
                            st.session_state.players = config_data["players"]
                            st.session_state.player_num = len(config_data["players"])
                        else:
                            st.error("玩家数量不足4人")

                        # 覆盖提示词
                        st.session_state.instructions.update(config_data["instructions"])

                        st.success("配置导入成功！")
                        file_name = imported_config.name.split('.')[0][:20]  # 截取文件名前20字符
                        st.session_state.alert_message = f"成功导入了备份配置：{file_name}"  # 设置弹窗消息
                        st.session_state.current_step = 3
                except Exception as e:
                    st.error(f"配置导入失败: {str(e)}")


    st.title("⚙️ 游戏配置 - 分步设置")

    # 步骤导航
    steps = ["1. 模型管理", "2. 玩家配置", "3. 提示词设置", "4. 完成"]
    current_step_index = st.session_state.get("current_step", 0)
    current_step = steps[current_step_index]

    # 步骤导航控件
    nav_cols = st.columns(len(steps))
    for idx, col in enumerate(nav_cols):
        with col:
            # 移除disabled属性和帮助提示
            if st.button(steps[idx],
                    key=f"nav_{idx}",
                    use_container_width=True,
                    type="primary" if idx == current_step_index else "secondary"):
                st.session_state.current_step = idx
                st.rerun()

    # 模型管理步骤
    if current_step == steps[0]:
        with st.container(border=True):
            st.subheader("🔧 模型管理")
            
            # 模型添加表单
            with st.form("model_form", border=True):
                cols = st.columns([2,1,2])
                with cols[0]:
                    model_name = st.text_input("模型名称*", help="例如: GPT-4-0125")
                with cols[1]:
                    api_key = st.text_input("API密钥*", type="password")
                with cols[2]:
                    base_url = st.text_input("API地址", value="https://api.openai.com/v1")
                model_config = st.text_input("模型名称（API参数）*", value="gpt-4-turbo")
                
                if st.form_submit_button("✅ 确认添加", use_container_width=True):
                    if model_name and api_key and model_config:
                        new_model = {
                            "name": model_name,
                            "api_key": api_key,
                            "base_url": base_url,
                            "model_name": model_config
                        }
                        # 检查重复名称
                        if any(m["name"] == model_name for m in st.session_state.models):
                            st.error("模型名称已存在！")
                        else:
                            st.session_state.models.append(new_model)
                            st.success(f"已添加模型: {model_name}")
                    else:
                        st.error("带*号的为必填项")

            # 模型列表管理
            st.subheader("已添加模型")
            if not st.session_state.models:
                st.info("暂无已配置模型")
            else:
                for idx, model in enumerate(st.session_state.models, 1):
                    with st.expander(f"{idx}. {model['name']}", expanded=False):
                        cols = st.columns([3,1])
                        with cols[0]:
                            st.markdown(f"""
                            - **API地址**: `{model['base_url']}`
                            - **模型标识**: `{model['model_name']}`
                            """)
                        with cols[1]:
                            if st.button("删除", key=f"del_model_{idx}"):
                                st.session_state.models.pop(idx-1)
                                st.rerun()

    # 玩家配置步骤
    elif current_step == steps[1]:
        with st.container(border=True):
            st.subheader("👥 玩家配置")

            # 玩家数量控制
            num_players = st.number_input("玩家数量",
                                        min_value=4,
                                        max_value=18,
                                        value=st.session_state.player_num if st.session_state.player_num else 8,
                                        step=1,
                                        key="player_num_control")

            # 动态调整玩家列表
            if len(st.session_state.players) != num_players:
                new_players = []
                for i in range(num_players):
                    if i < len(st.session_state.players):
                        new_players.append(st.session_state.players[i])
                    else:
                        new_players.append({"role": "villager", "model": ""})
                st.session_state.players = new_players
                st.session_state.player_num = num_players

            # 角色选项配置
            roles_to_select = stander_roles + ["自定义"]
            role_names = {
                "werewolf": "🐺 狼人",
                "villager": "👨🌾 村民",
                "witch": "🧙♀ 女巫",
                "seer": "🔮 预言家"
            }

            cols = st.columns(4)
            for i in range(num_players):
                with cols[i%4]:
                    with st.container(border=True):
                        st.markdown(f"### 玩家 {i+1}")

                        # 角色选择
                        current_role = st.session_state.players[i]["role"] if st.session_state.players[i]["role"] else "villager"
                        new_role = st.selectbox(
                            "角色",
                            options=roles_to_select,
                            index=stander_roles.index(current_role) if current_role in stander_roles else len(roles_to_select)-1,
                            format_func=lambda x: role_names.get(x,"❓"+x),
                            key=f"role_{i}"
                        )

                        if new_role == "自定义":
                            new_role = st.text_input("自定义角色名",
                                                    key=f"custom_role_{i}",
                                                    value=current_role)
                            if new_role in stander_roles:
                                st.error("自定义角色名不能与标准角色名重复")
                                new_role = current_role
                            st.session_state.instructions[new_role] = ""


                        # 模型选择
                        if st.session_state.models:
                            current_model = st.session_state.players[i]["model"]
                            model_names = [m["name"] for m in st.session_state.models]
                            default_idx = model_names.index(current_model) if current_model in model_names else 0

                            new_model = st.selectbox(
                                "使用模型",
                                options=model_names,
                                index=default_idx,
                                key=f"model_{i}"
                            )
                            st.session_state.players[i] = {"role": new_role, "model": new_model}
                        else:
                            st.error("请先添加至少一个模型")

    # 提示词设置步骤
    elif current_step == steps[2]:
        with st.container(border=True):
            st.subheader("📝 提示词设置")

            # 角色名称映射
            role_names = {
                "werewolf": "🐺 狼人",
                "villager": "👨🌾 村民",
                "witch": "🧙♀ 女巫",
                "seer": "🔮 预言家"
            }

            # 通用提示词设置
            st.session_state.instructions["general"] = st.text_area(
                "通用提示词",
                height=400,
                value=st.session_state.instructions.get("general", ""),
                help="使用Markdown格式编写，支持代码块等格式",
                key="general_inst"
            )

            cols = st.columns(2)
            with cols[0]:
                if st.button("恢复默认提示词",key="reset_general"):
                    st.session_state.instructions["general"] = read_json("./config/default_instructions.json")["general"]
                    st.rerun()
            with cols[1]:
                if st.button("清空提示词",key="clear_general"):
                    st.session_state.instructions["general"] = ""
                    st.rerun()

            # 分角色提示词设置
            all_roles = list(set([i["role"] for i in st.session_state.players]))
            role_tabs = st.tabs([role_names.get(r,"❓"+r) for r in all_roles])
            for idx, tab in enumerate(role_tabs):
                with tab:
                    role = all_roles[idx]
                    st.session_state.instructions[role] = st.text_area(
                        f"{role_names.get(role,role)}提示词",
                        value=st.session_state.instructions.get(role, ""),
                        height=400,
                        key=f"edit_{role}"
                    )
                    cols = st.columns(2)
                    with cols[0]:
                        if st.button("恢复默认提示词",key=f"reset_{role}"):
                            st.session_state.instructions[role] = read_json("./config/default_instructions.json").get(role, "")
                            st.rerun()
                    with cols[1]:
                        if st.button("清空提示词",key=f"clear_{role}"):
                            st.session_state.instructions[role] = ""
                            st.rerun()

    # 完成配置步骤
    else:
        with st.container(border=True):
            st.subheader("✅ 配置完成")
            st.text_input("游戏名称", value=game_name, key="game_name")

            # 配置预览
            with st.expander("📋 当前配置概览"):
                config_preview = {
                    "模型列表": [m["name"] for m in st.session_state.models],
                    "玩家配置": [
                        f"玩家{i+1}: {p['role']} => {p['model']}" 
                        for i, p in enumerate(st.session_state.players)
                    ],
                    "提示词摘要": {
                        "general": st.session_state.instructions["general"][:50] + "..." if st.session_state.instructions["general"] else "空",
                        "werewolf": st.session_state.instructions["werewolf"][:50] + "..." if st.session_state.instructions["werewolf"] else "空",
                        "villager": st.session_state.instructions["villager"][:50] + "..." if st.session_state.instructions["villager"] else "空",
                        "witch": st.session_state.instructions["witch"][:50] + "..." if st.session_state.instructions["witch"] else "空",
                        "seer": st.session_state.instructions["seer"][:50] + "..." if st.session_state.instructions["seer"] else "空"
                    }
                }
                st.json(config_preview)

            # 配置验证
            valid = True
            validation_errors = []

            if not st.session_state.models:
                validation_errors.append("至少需要配置一个模型")
                valid = False

            for i, player in enumerate(st.session_state.players):
                if not player["model"]:
                    validation_errors.append(f"玩家 {i+1} 未选择模型")
                    valid = False
                if player["model"] not in [m["name"] for m in st.session_state.models]:
                    validation_errors.append(f"玩家 {i+1} 使用的模型不存在")
                    valid = False

            is_werewolve = False
            for player in st.session_state.players:
                if player["role"] == "werewolf":
                    is_werewolve = True
                    break
            if not is_werewolve:
                validation_errors.append("至少需要一个狼人")
                valid = False

            has_custom_role = False
            for i in st.session_state.players:
                if i["role"] not in stander_roles:
                    has_custom_role = True
                    break

            game_mode = st.selectbox("选择游戏模式", ["全自动模式", "人工模式（你是上帝❗）"], key="webui_mode",index = 1 if has_custom_role else 0)

            if has_custom_role and game_mode != "人工模式（你是上帝❗）":
                validation_errors.append("存在自定义角色时只能选择人工模式")
                valid = False
            # 显示验证结果
            if validation_errors:
                st.error("配置存在问题：\n- " + "\n- ".join(validation_errors))
            else:
                st.success("所有配置验证通过！")


            # 游戏启动按钮
            if valid and st.button("🚀 启动游戏", type="primary", use_container_width=True):
                if 1:
                    # 构建配置数据
                    config = {
                        "apis": {m["name"]: m for m in st.session_state.models},
                        "players_info": {
                            str(i+1): {"model": p["model"], "role": p["role"]}
                            for i, p in enumerate(st.session_state.players)
                        },
                        "instructions": st.session_state.instructions
                    }
                    config["players_info"]["0"] = f"这是一局有{st.session_state.player_num}名玩家的狼人杀游戏，其中有"
                    players_count = {}
                    for i in st.session_state.players:
                        players_count[player_role_to_chinese.get(i["role"],i["role"])] = players_count.get(player_role_to_chinese.get(i["role"],i["role"]), 0) + 1
                    for i in players_count:
                        config["players_info"]["0"] += f"{players_count[i]}名{i}，"
                    config["players_info"]["0"] = config["players_info"]["0"][:-1] + "。"

                    # 创建游戏对象
                    game = Game(
                        game_name=game_name,
                        players_info_path=config["players_info"],
                        apis_path=config["apis"],
                        instructions_path=config["instructions"],
                        webui_mode=True,
                        from_dict=True
                    )

                    # 保存游戏状态
                    st.session_state.game = game
                    st.session_state.current_page = 'auto_game' if game_mode == "全自动模式" else 'manual_game'
                    st.session_state.initialized = True
                    st.rerun()
    if 'alert_message' in st.session_state:
        st.components.v1.html(f"""
        <script>
            alert("{st.session_state.alert_message}");
        </script>
        """)
        del st.session_state.alert_message  # 显示后立即清除


def format_log_message(context, game):
    role = "上帝" if context.source_id == 0 else next(
        (p.role for p in game.players if p.id == context.source_id), "未知"
    )
    
    # 处理思考过程折叠
    content = context.content
    if '<think>' in content and '</think>' in content:
        import re
        content = re.sub(
            r'<think>\s*\n(.*?)\n</think>',  # 匹配思考内容
            r'<details style="margin-top: 5px;"><summary>🤔 思考结束（点击展开）</summary><div style="padding: 8px; background: rgba(0,0,0,0.05);">\1</div></details>',
            content,
            flags=re.DOTALL
        )
    elif '<think>' in content:
        import re
        content = re.sub(
            r'(<think>[\s\S]*)',  # 匹配思考内容
            r'<details style="margin-top: 5px;"><summary>🚧🤔 思考中（点击展开）...</summary><div style="padding: 8px; background: rgba(0,0,0,0.05);">\1</div></details>',
            content,
            flags=re.DOTALL
        )
    content = content.replace('\n', '<br>')  # 处理普通换行

    return f"""<div style='
    padding: 10px;
    margin: 8px 0;
    border-radius: 8px;
    background-color: {ROLE_COLORS.get(role, "#F0F0F0")};
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
'><a name="source_id_{context.source_id}"></a>
    <strong style='font-size: 0.9em;'>{player_role_to_chinese.get(role, "未知")}{ROLE_ICONS.get(role, "❓")} (玩家{context.source_id})</strong>
    <div style='margin-top: 5px; font-size: 0.95em;'>
        {content}
    </div>
</div>"""


def auto_game_page():

    st.set_page_config(page_title="狼人杀😋", page_icon="🐺", layout="wide", initial_sidebar_state="collapsed", menu_items={"About":"https://github.com/xxh16384/LLMsWerewolves"})

    st.title("🎭 狼人杀！")
    game = st.session_state.game

    # 侧边栏显示控制按钮
    with st.sidebar:
        if st.button("↩️ 返回配置"):
            # 安全终止线程的逻辑
            if hasattr(st.session_state, 'phase_thread') and st.session_state.phase_thread:
                if st.session_state.phase_thread.is_alive():
                    # 发送终止信号
                    if st.session_state.phase_progress:
                        st.session_state.phase_progress.set()
                    # 等待线程结束
                    with st.spinner("正在终止线程..."):
                        st.session_state.phase_thread.join(timeout=10)
                    # 强制清除
                    with st.spinner("强制终止线程..."):
                        if st.session_state.phase_thread.is_alive():
                            time.sleep(1)
                            st.session_state.phase_thread = None

            # 重置游戏状态
            st.session_state.current_page = 'config'
            st.session_state.game = None
            st.session_state.initialized = False
            st.rerun()

    if st.session_state.game and st.session_state.initialized:
        game = st.session_state.game

        # 创建选项卡布局
        tab1, tab2 = st.tabs(["💬 聊天日志", "👥 玩家状态"])

        with tab2:  # 玩家状态选项卡
            st.empty()

        with tab1:  # 聊天日志选项卡
            days, phase = game.get_game_stage()
            st.info(f"当前阶段：第{days}天 {'☀️ 白天' if phase else '🌙 夜晚'}")

            stages = [f"第{i//2+1}天{'☀️ 白天' if (i+1)%2 else '🌙 夜晚'}" for i in range(game.stage+1)]
            display_stage = st.selectbox("聊天记录展示阶段", stages, key="display_stage", index=len(stages)-1)
            # 日志容器
            log_container = st.empty()

            def update_logs():
                current_logs = Context.get_chat_log(game, stages.index(display_stage)) if Context.get_chat_log(game, stages.index(display_stage)) else []
                formatted_logs = "".join([str(format_log_message(c, game)) for c in current_logs])

                log_container.markdown(f"""
                <div id="log-container" style="overflow-y: auto;max-height: 60vh;">
                    {formatted_logs}
                </div>
                """, unsafe_allow_html=True)

                st.components.v1.html("""<script>
                window.location.hash = "存活玩家状态";
                </script>""", height=0)
                with tab2:
                    days, phase = game.get_game_stage()
                    st.info(f"当前阶段：第{days}天 {'☀️ 白天' if phase else '🌙 夜晚'}")
                    players = game.get_players(alive=False)
                    cols = st.columns(3)
                    for i, player in enumerate(players):
                        with cols[i % 3]:
                            role_color = ROLE_COLORS.get(player.role, "#FFF")
                            st.markdown(f"""<div style='text-align: center; padding: 12px; border-radius: 12px; background-color: {role_color};'>
                                <h4>玩家{player.id}</h4>
                                <p>{ROLE_ICONS.get(player.role,"❓"+player.role)}</p>
                                <p>{'✅ 存活' if player.alive else '❌ 出局'}</p>
                            </div>""", unsafe_allow_html=True)

            if game.game_over():
                st.balloons()
                game.get_winner()
                st.success("游戏结束！")
                update_logs()
                st.stop()
                st.rerun()

            # 阶段控制按钮
            if not game.game_over():
                btn_disabled = bool(
                    (game and game.game_over())
                    or (st.session_state.phase_thread and st.session_state.phase_thread.is_alive())
                )
                btn = st.button("⏭️ 进入下一阶段",
                                disabled=btn_disabled,
                                help="游戏已结束" if (game and game.game_over()) else "进入下一阶段")
            else:
                btn = False

            # 无论是否点击按钮都执行update_logs
            update_logs()  # 新增此行保证日志持续更新

            if btn:
                btn = False
                btn_disabled = False
                if st.session_state.phase_thread and st.session_state.phase_thread.is_alive():
                    st.warning("当前阶段正在处理中，请稍候...")
                    st.rerun()
                    return
                else:
                    with st.spinner("处理阶段..."), st.session_state.game_lock:
                        # 二次验证游戏状态（防止点击瞬间状态变化）
                        if game.game_over():
                            st.rerun()
                            return

                        phase_progress = Event()
                        st.session_state.phase_progress = phase_progress

                        def run_phase(progress_event):
                            try:
                                # 每次循环前检查游戏状态
                                if game.game_over():
                                    progress_event.set()
                                    return

                                if not game.game_over() and not progress_event.is_set():game.day_night_change()
                                days, phase = game.get_game_stage()

                                if not phase:
                                    # 每个操作前检查状态
                                    # game对象会自动生成killing toninght列表，在昼夜更替的时候踢出玩家
                                    if not game.game_over() and not progress_event.is_set(): game.werewolf_killing()
                                    if not game.game_over() and not progress_event.is_set(): game.seer_seeing()
                                    if not game.game_over() and not progress_event.is_set(): game.witch_operation()
                                else:
                                    if not game.game_over() and not progress_event.is_set(): game.public_discussion()
                                    if not game.game_over() and not progress_event.is_set():
                                        result = game.vote()
                                        game.out([find_max_key(result)])


                            except Exception as e:
                                st.error(f"阶段处理失败：{e}")
                            finally:
                                progress_event.set()

                        # 启动线程前再次检查
                        if not game.game_over():
                            st.session_state.phase_thread = Thread(target=run_phase, args=(phase_progress,), daemon=True)
                            st.session_state.phase_thread.start()
            if game.game_over():
                st.balloons()
                game.get_winner()
                st.success("游戏结束！")
                update_logs()
                st.stop()
                st.rerun()

            def monitor_phase(progress_event):
                while True:
                    # 双重终止条件 + 游戏状态检查
                    if progress_event.is_set() or game.game_over():
                        progress_event.set()  # 确保传播终止信号
                        st.session_state.phase_thread = None
                        st.session_state.phase_progress = None
                        break
                    time.sleep(2)
                    st.rerun()

            if st.session_state.phase_thread and st.session_state.phase_thread.is_alive():
                with st.spinner("响应中..."):
                    if st.session_state.phase_progress:
                        monitor_phase(st.session_state.phase_progress)

        if game.game_over():
            st.balloons()
            game.get_winner()
            st.success("游戏结束！")
            update_logs()
            st.stop()
            st.rerun()

        if 'alert_message' in st.session_state:
            st.components.v1.html(f"""
            <script>
                alert("{st.session_state.alert_message}");
            </script>
            """)
            del st.session_state.alert_message
    else:
        st.info("请先创建游戏")


def manual_game_page():
    st.set_page_config(page_title="狼人杀😋", page_icon="🐺", layout="wide", initial_sidebar_state="expanded", menu_items={"About":"https://github.com/xxh16384/LLMsWerewolves"})

    st.title("🎭 狼人杀！")
    game = st.session_state.game

    # 侧边栏显示控制按钮
    with st.sidebar:
        if st.button("↩️ 返回配置"):
            # 安全终止线程的逻辑（与auto_game_page保持一致）
            if hasattr(st.session_state, 'msg_thread') and st.session_state.msg_thread:
                if st.session_state.msg_thread.is_alive():
                    if st.session_state.msg_progress:
                        st.session_state.msg_progress.set()
                    with st.spinner("正在终止线程..."):
                        st.session_state.msg_thread.join(timeout=10)
                    with st.spinner("强制终止线程..."):
                        if st.session_state.msg_thread.is_alive():
                            time.sleep(1)
                            st.session_state.msg_thread = None

            st.session_state.current_page = 'config'
            st.session_state.game = None
            st.session_state.initialized = False
            st.rerun()

        st.divider()
        st.title("📕✍ 人工操作")

        with st.expander("💬 对话操作", expanded=True):
            if st.session_state.game:
                selected_action = st.selectbox("选择操作",options=["上帝广播","私聊","公共聊天","群发公共聊天"],key="selected_action", index=0)

                player_options = [f"{player.id}号{player_role_to_chinese.get(player.role,player.role)}" for player in st.session_state.game.get_players(t="object")] + ["全体存活玩家","全体玩家"]

                match selected_action:
                    case "上帝广播":
                        default_options = len(player_options)-1
                    case "私聊"|"公共聊天":
                        default_options = 0
                    case "群发公共聊天":
                        default_options = len(player_options)-2

                selected_player = st.selectbox("选择玩家", options=player_options,key="selected_player", index=default_options)
                selected_player_id = player_options.index(selected_player)
                content = st.text_area("请输入内容", key="content")

                if st.button("发送", disabled= not st.session_state.msg_progress.is_set() if st.session_state.msg_progress else False):
                    msg_progress = Event()
                    st.session_state.msg_progress = msg_progress

                    def send_message():
                        try:
                            match selected_action:
                                case "上帝广播":
                                    if selected_player_id != len(player_options)-1:
                                        raise ValueError("上帝广播仅支持全体玩家")
                                    game.broadcast(content)
                                case "私聊":
                                    if selected_player_id == len(player_options)-1 or selected_player_id == len(player_options)-2:
                                        raise ValueError("私聊仅支持单个玩家")
                                    target_id = game.get_players(t="object")[selected_player_id].id
                                    game.private_chat(target_id, content)
                                case "公共聊天":
                                    if selected_player_id == len(player_options)-1 or selected_player_id == len(player_options)-2:
                                        raise ValueError("公共聊天仅支持单个玩家")
                                    target_id = game.get_players(t="object")[selected_player_id].id
                                    game.public_chat(target_id, content)
                                case "群发公共聊天":
                                    if selected_player_id != len(player_options)-2:
                                        raise ValueError("群发公共聊天仅支持全体存活玩家")
                                    Context(game,0,content,visible_ids=game.get_players(t="id",alive=False))
                                    for player in game.get_players(alive=(selected_player == "全体存活玩家")):
                                        game.public_chat(player.id, content,False)
                        except Exception as e:
                            st.session_state.msg_queue.put(("error", f"发送失败: {str(e)}"))
                        finally:
                            msg_progress.set()
                            st.session_state.msg_queue.put(("status", False))

                    st.session_state.msg_thread = Thread(target=send_message, daemon=True)
                    from streamlit.runtime.scriptrunner import add_script_run_ctx
                    add_script_run_ctx(st.session_state.msg_thread)
                    st.session_state.msg_thread.start()

                if st.session_state.msg_queue and not st.session_state.msg_queue.empty():
                    msg_type, content = st.session_state.msg_queue.get()
                    if msg_type == "error":
                        st.error(content)
                        time.sleep(1)
                    st.rerun()

        with st.expander("☀️🌙游戏阶段更替", expanded=True):
            if st.session_state.game:
                generate_broadcast = st.radio("是自动否生成广播", options=["是", "否"], key="generate_broadcast", index=0)
                if st.button("更替", disabled= not st.session_state.msg_progress.is_set() if st.session_state.msg_progress else False):
                    game.stage += 1
                    days,morning_dusk = game.get_game_stage()
                    if generate_broadcast == "是":
                        game.broadcast(f"现在是第{days}天{'白天' if morning_dusk else '晚上'}")

        with st.expander("👥 玩家管理", expanded=True):
            players_out = st.text_input("请输入出局玩家编号，用英文逗号分隔", key="out_player_name",value="")
            try:
                if st.button("踢出玩家", disabled= not st.session_state.msg_progress.is_set() if st.session_state.msg_progress else False):
                    players_out_id = [int(player_id) for player_id in players_out.split(",")]
                    game.out(players_out_id)
                    st.success(f"踢出成功，已踢出{str(players_out_id)[1:-1]}号玩家")
                    st.rerun()
            except Exception as e:
                st.error(f"踢出失败: {str(e)}")
            st.divider()
            players_in = st.text_input("请输入重新加入的玩家编号，用英文逗号分隔", key="add_player_name",value="")
            try:
                if st.button("加入玩家", disabled= not st.session_state.msg_progress.is_set() if st.session_state.msg_progress else False):
                    players_out_id = [int(player_id) for player_id in players_out.split(",")]
                    game.no_out(players_out_id)
                    st.success(f"重新加入成功，{str(players_out_id)[1:-1]}号玩家重返游戏")
                    st.rerun()
            except Exception as e:
                st.error(f"加入失败: {str(e)}")


    # 主界面布局
    if st.session_state.game and st.session_state.initialized:
        tab1, tab2 = st.tabs(["💬 聊天日志", "👥 玩家状态"])
        
        with tab2:
            st.empty()

        with tab1:  # 聊天日志
            days, phase = game.get_game_stage()
            st.info(f"当前阶段：第{days}天 {'☀️ 白天' if phase else '🌙 夜晚'}")
            stages = [f"第{i//2+1}天{'☀️ 白天' if (i+1)%2 else '🌙 夜晚'}" for i in range(game.stage+1)]
            display_stage = st.selectbox("聊天记录展示阶段", stages, key="display_stage", index=len(stages)-1)
            log_container = st.empty()

            def update_logs():
        
                current_logs = Context.get_chat_log(game, stages.index(display_stage)) if Context.get_chat_log(game, stages.index(display_stage)) else []
                formatted_logs = "".join([str(format_log_message(c, game)) for c in current_logs])

                log_container.markdown(f"""
                <div id="log-container" style="overflow-y: auto; max-height: 70vh;">
                    {formatted_logs}
                </div>
                """, unsafe_allow_html=True)

                # 自动滚动到底部
                st.components.v1.html("""
                <script>
                    var logContainer = document.getElementById('log-container');
                    logContainer.scrollTop = logContainer.scrollHeight;
                </script>
                """)
                with tab2:  # 玩家状态
                    days, phase = game.get_game_stage()
                    st.info(f"当前阶段：第{days}天 {'☀️ 白天' if phase else '🌙 夜晚'}")

                    players = game.get_players(alive=False)
                    cols = st.columns(3)
                    for i, player in enumerate(players):
                        with cols[i % 3]:
                            role_color = ROLE_COLORS.get(player.role, "#FFF")
                            st.markdown(f"""<div style='text-align: center; padding: 12px; border-radius: 12px;background-color: {role_color};'>
                                <h4>玩家{player.id}</h4>
                                <p>{ROLE_ICONS.get(player.role,"❓"+player.role)}</p>
                                <p>{'✅ 存活' if player.alive else '❌ 出局'}</p>
                            </div>""", unsafe_allow_html=True)


            update_logs()

        # 消息发送监控线程
        def monitor_message(progress_event):
            while not progress_event.is_set():
                time.sleep(0.5)
                if progress_event.is_set():
                    st.session_state.msg_thread = None
                    st.session_state.msg_progress = None
                    st.rerun()
                st.rerun()

        if st.session_state.get('msg_thread') and st.session_state.msg_thread.is_alive():
            with st.spinner("消息发送中..."):
                monitor_message(st.session_state.msg_progress)

        # 游戏结束处理
        if game.game_over():
            st.balloons()
            winner = game.get_winner()
            st.success(f"游戏结束！胜利方：{winner}")
            st.stop()
    else:
        st.info("请先创建游戏")

    if 'alert_message' in st.session_state:
        st.components.v1.html(f"""
        <script>
            alert("{st.session_state.alert_message}");
        </script>
        """)
        del st.session_state.alert_message


def main():
    init_session_state()

    try:
        if st.session_state.current_page == 'config':
            config_page()
        elif st.session_state.current_page == 'auto_game' and st.session_state.game:
            auto_game_page()
        elif st.session_state.current_page == 'manual_game' and st.session_state.game:
            manual_game_page()
        else:
            st.warning("游戏初始化失败，请返回配置页面")
    finally:
        # 修复后的全局清理逻辑
        if not st.session_state.game and 'phase_thread' in st.session_state and st.session_state.phase_thread is not None:
            if st.session_state.phase_thread.is_alive():
                st.session_state.phase_progress.set()
                st.session_state.phase_thread.join(timeout=1)

if __name__ == "__main__":
    main()