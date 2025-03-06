import streamlit as st
from main import Game, Context, find_max_key
import time
from threading import Thread, Lock, Event
from queue import Queue

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
    # 新增以下初始化语句
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

# 配置页面
def config_page():
    st.title("⚙️ 游戏配置")
    
    with st.form("game_config"):
        # 游戏基础配置
        game_name = st.text_input("游戏名称", "狼人杀游戏1")
        instructions = st.file_uploader("游戏提示词（instructions.json）", type=["json"])
        player_info = st.file_uploader("玩家信息（player_info.json）", type=["json"])
        apis = st.file_uploader("API配置（apis.json）", type=["json"])

        # 提交按钮
        if st.form_submit_button("🚀 开始游戏"):
            if all([instructions, player_info, apis]):
                try:
                    # 创建游戏对象
                    game = Game(
                        game_name,
                        player_info.getvalue(),
                        apis.getvalue(),
                        instructions.getvalue(),
                        webui_mode=True
                    )
                    
                    # 保存到session state
                    st.session_state.game = game
                    st.session_state.current_page = 'game'
                    # 在创建游戏对象后添加以下代码
                    st.session_state.initialized = True  # <-- 新增这一行
                    st.session_state.log_cache = []
                    st.session_state.phase_thread = None
                    st.session_state.phase_progress = None
                    st.rerun()
                except Exception as e:
                    st.error(f"游戏创建失败：{str(e)}")
            else:
                st.error("请上传所有配置文件！")


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
            r'<details style="margin-top: 5px;"><summary>🤔 思考结束（点击展开）...</summary><div style="padding: 8px; background: rgba(0,0,0,0.05);">\1</div></details>',
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
    st.title("🎭 狼人杀对局进行中")
    game = st.session_state.game

    # 侧边栏显示控制按钮
    with st.sidebar:
        if st.button("↩️ 返回配置"):
            st.session_state.current_page = 'config'
            st.session_state.game = None
            st.session_state.initialized = False  # <-- 新增重置初始化状态
            st.rerun()


    if st.session_state.game and st.session_state.initialized:
        game = st.session_state.game

        # 创建选项卡布局
        tab1, tab2 = st.tabs(["💬 聊天日志", "👥 玩家状态"])

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

            # 阶段控制按钮
            if st.button("⏭️ 进入下一阶段"):
                with st.spinner("处理阶段..."), st.session_state.game_lock:
                    if st.session_state.phase_thread and st.session_state.phase_thread.is_alive():
                        if st.session_state.phase_progress:
                            st.session_state.phase_progress.put("skip")
                        st.session_state.phase_thread.join(timeout=2)

                    phase_progress = Queue()
                    st.session_state.phase_progress = phase_progress

                    def run_phase(progress_queue):
                        try:
                            game.day_night_change()
                            days, phase = game.get_game_stage()

                            if not phase:
                                game.werewolf_killing()
                                game.seer_seeing()
                                game.witch_operation()
                            else:
                                game.public_discussion()
                                result = game.vote()
                                game.out([find_max_key(result)])
                        except Exception as e:
                            st.error(f"阶段处理失败：{e}")
                        finally:
                            progress_queue.put("done")

                    st.session_state.phase_thread = Thread(target=run_phase, args=(phase_progress,))
                    st.session_state.phase_thread.start()

            def monitor_phase(progress_queue):
                start_time = time.time()
                while time.time() - start_time < 60:
                    with st.session_state.game_lock:
                        update_logs()

                    time.sleep(2)
                    st.rerun()

                    try:
                        if progress_queue.get_nowait() == "done":
                            break
                    except:
                        continue

            if st.session_state.phase_thread and st.session_state.phase_thread.is_alive():
                with st.spinner("响应中..."):
                    if st.session_state.phase_progress:
                        monitor_phase(st.session_state.phase_progress)
                
                if game.game_over():
                    st.balloons()
                    st.success("游戏结束！")
                    st.stop()
            else:
                update_logs()

        with tab2:  # 玩家状态选项卡
            st.empty()

    else:
        st.info("请先创建游戏")
        

def main():
    init_session_state()

    if st.session_state.current_page == 'config':
        config_page()
    elif st.session_state.current_page == 'game' and st.session_state.game:
        game_page()
    else:
        st.warning("游戏初始化失败，请返回配置页面")

if __name__ == "__main__":
    main()