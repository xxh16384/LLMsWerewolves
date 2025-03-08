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

def init_session_state():
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'config'
    if 'game' not in st.session_state:
        st.session_state.game = None
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    if 'log_cache' not in st.session_state:
        st.session_state.log_cache = []
    if 'game_lock' not in st.session_state:
        st.session_state.game_lock = Lock()
    if 'phase_thread' not in st.session_state:
        st.session_state.phase_thread = None
    if 'phase_progress' not in st.session_state:
        st.session_state.phase_progress = None
    if 'models' not in st.session_state:
        st.session_state.models = []
    if 'players' not in st.session_state:
        st.session_state.players = []
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
                                        value=len(st.session_state.players) if st.session_state.players else 8,
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
            roles = ["werewolf", "villager", "witch", "seer"]
            role_names = {
                "werewolf": "🐺 狼人",
                "villager": "👨🌾 村民",
                "witch": "🧙♀ 女巫",
                "seer": "🔮 预言家"
            }

            # 生成玩家配置项
            cols = st.columns(4)
            for i in range(num_players):
                with cols[i%4]:
                    with st.container(border=True):
                        st.markdown(f"### 玩家 {i+1}")
                        
                        # 角色选择
                        current_role = st.session_state.players[i]["role"]
                        new_role = st.selectbox(
                            "角色",
                            options=roles,
                            index=roles.index(current_role) if current_role in roles else 1,
                            format_func=lambda x: role_names[x],
                            key=f"role_{i}"
                        )

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
            role_tabs = st.tabs(["🐺 狼人", "👨🌾 村民", "🧙♀ 女巫", "🔮 预言家"])
            for idx, tab in enumerate(role_tabs):
                with tab:
                    role = ["werewolf", "villager", "witch", "seer"][idx]
                    st.session_state.instructions[role] = st.text_area(
                        f"{role_names[role]}提示词",
                        value=st.session_state.instructions.get(role, ""),
                        height=400,
                        key=f"edit_{role}"
                    )
                    cols = st.columns(2)
                    with cols[0]:
                        if st.button("恢复默认提示词",key=f"reset_{role}"):
                            st.session_state.instructions[role] = read_json("./config/default_instructions.json")[role]
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
                    config["players_info"]["0"] = f"这是一局有{len(st.session_state.players)}名玩家的狼人杀游戏，其中有"
                    players_count = {}
                    for i in st.session_state.players:
                        players_count[player_role_to_chinese[i["role"]]] = players_count.get(i["role"], 0) + 1
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
                    st.session_state.current_page = 'game'
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


def game_page():

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
            st.session_state.log_cache = []
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

            # 日志容器
            log_container = st.empty()

            def update_logs():
                current_logs = Context.contexts.get(game, [])
                new_logs = current_logs[len(st.session_state.log_cache):]

                formatted_logs = "".join([str(format_log_message(c, game)) for c in st.session_state.log_cache + new_logs])

                log_container.markdown(f"""
                <div id="log-container" style="overflow-y: auto;max-height: 60vh;">
                    {formatted_logs}
                </div>
                """, unsafe_allow_html=True)

                st.session_state.log_cache = current_logs.copy()
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
                                <p>{ROLE_ICONS.get(player.role,"❓")}</p>
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
                btn = st.button("⏭️ 进入下一阶段",
                                disabled=game.game_over() or (st.session_state.phase_thread and st.session_state.phase_thread.is_alive()),
                                help="游戏已结束" if game.game_over() else "进入下一阶段")
            else:
                btn = False
            if btn:
                if st.session_state.phase_thread and st.session_state.phase_thread.is_alive():
                    st.warning("当前阶段正在处理中，请稍候...")
                    return
                with st.spinner("处理阶段..."), st.session_state.game_lock:
                    # 二次验证游戏状态（防止点击瞬间状态变化）
                    if game.game_over():
                        st.rerun()
                        return
                    
                    phase_progress = Event()
                    st.session_state.phase_progress = phase_progress

                    def run_phase(progress_event):
                        try:
                            while not (progress_event.is_set() or game.game_over()):
                                # 每次循环前检查游戏状态
                                if game.game_over():
                                    progress_event.set()
                                    return
                                
                                game.day_night_change()
                                days, phase = game.get_game_stage()

                                if not phase:
                                    # 每个操作前检查状态
                                    if not game.game_over(): game.werewolf_killing()
                                    if not game.game_over(): game.seer_seeing()
                                    if not game.game_over(): game.witch_operation()
                                else:
                                    if not game.game_over(): game.public_discussion()
                                    if not game.game_over():
                                        result = game.vote()
                                        game.out([find_max_key(result)])
                                
                                # 每次操作后立即检查
                                if game.game_over():
                                    progress_event.set()
                                    return

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
                    
                    with st.session_state.game_lock:
                        update_logs()
                    
                    time.sleep(2)
                    st.rerun()
                update_logs()

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
            
        update_logs()

    else:
        st.info("请先创建游戏")


def main():
    init_session_state()

    try:
        if st.session_state.current_page == 'config':
            config_page()
        elif st.session_state.current_page == 'game' and st.session_state.game:
            game_page()
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