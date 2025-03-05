import streamlit as st
from main import Game, Context, find_max_key
import time
import json
from threading import Thread, Lock, Event
from queue import Queue

# 角色颜色配置
ROLE_COLORS = {
    "上帝": "#2c3e50",    # 深灰蓝
    "werewolf": "#e74c3c",  # 红色
    "villager": "#27ae60",  # 绿色
    "witch": "#8e44ad",     # 紫色
    "seer": "#2980b9"       # 蓝色
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


# 初始化session状态（确保在主线程初始化）
def init_session_state():
    required_keys = {
        'game': None,
        'log_cache': [],
        'game_lock': Lock(),
        'phase_thread': None,
        'phase_progress': None,
        'uploaded_files': {},
        'initialized': False,
        'log_container': None
    }
    for key, value in required_keys.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

def format_log_message(context, game):
    role = "上帝" if context.source_id == 0 else next(
        (p.role for p in game.players if p.id == context.source_id), "未知"
    )
    # 添加安全判断
    streaming_style = "border-left: 3px solid #f39c12; padding-left: 10px;" if getattr(context, 'is_streaming', False) else ""
    
    return f"""
<div style='
    padding: 12px;
    margin: 8px 0;
    border-radius: 8px;
    background: {ROLE_COLORS.get(role, "#f1f1f1")};
    color: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
'><a name="source_id_{context.source_id}"></a>
    <strong style='font-size: 0.9em;'>{player_role_to_chinese.get(role, "未知")}{ROLE_ICONS.get(role, "❓")} (玩家{context.source_id})</strong>
    <div style='margin-top: 5px; font-size: 0.95em;'>
        {context.content.replace('\n', '<br>')}
    </div>
</div>"""  # 显式闭合div标签 <source_id data="webui.py" />

# 主界面
st.title("🎭 狼人杀AI对局系统")

# 侧边栏配置
with st.sidebar:
    st.title("🎮 游戏配置")
    game_name = st.text_input("输入游戏名称", "狼人杀游戏1")
    files = {
    "instructions":st.file_uploader("上传游戏提示词（instructions.json）", type=["json"]),
    "player_info":st.file_uploader("上传玩家信息（player_info.json）", type=["json"]),
    "apis":st.file_uploader("上传API配置（apis.json）", type=["json"])
    }
    
    if st.button("创建新游戏"):
        with st.spinner("初始化游戏..."), st.session_state.game_lock:
            st.session_state.game = None
            st.session_state.log_cache = []
            st.session_state.phase_thread = None
            st.session_state.phase_progress = None  # 重置为None
            st.session_state.initialized = False
            
            st.session_state.game = Game(
                game_name,
                files["player_info"].getvalue(),
                files["apis"].getvalue(),
                files["instructions"].getvalue(),
                webui_mode=True
            )
            st.session_state.initialized = True
            st.session_state.log_container = st.empty()
            st.success(f"游戏 {game_name} 创建成功！")

if st.session_state.game and st.session_state.initialized:
    game = st.session_state.game
    
    log_container = st.empty()
    
    st.subheader("👥 玩家状态")
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
    
    def update_logs():
        current_logs = Context.contexts.get(game, [])
        new_logs = current_logs[len(st.session_state.log_cache):]
        
        formatted_logs = "".join([str(format_log_message(c, game)) for c in st.session_state.log_cache + new_logs])
        
        # 更新日志容器内容
        log_container.markdown(f"""
<div id="log-container" style="overflow-y: auto;">
    {formatted_logs}
</div>
        """, unsafe_allow_html=True)

        # 更新缓存
        st.session_state.log_cache = current_logs.copy()

        st.components.v1.html("""<script>
window.location.hash = "存活玩家状态";
</script>
""", height=0)

    
    cols = st.columns(len(players))
    for col, player in zip(cols, players):
        with col:
            status = "🟢" if player.alive else "⚪"
            role_icon = ROLE_ICONS.get(player.role, "")
            col.markdown(f"""
                <div style='
                    padding: 12px;
                    border-radius: 8px;
                    background: {ROLE_COLORS.get(player.role, "#f1f1f1")};
                    color: white;
                    text-align: center;
                '>
                    <div style="font-size: 1.5em">{status}{role_icon}</div>
                    <div>玩家 {player.id}</div>
                    <div style="font-size: 0.9em">{'存活' if player.alive else '出局'}</div>
                </div>
            """, unsafe_allow_html=True)

# 游戏日志显示
if st.session_state.game:
    game = st.session_state.game
    
    # 阶段控制按钮
    is_disabled = False
    if st.session_state.phase_thread and st.session_state.phase_thread.is_alive():
        is_disabled = True
    
    if st.button("⏭️ 进入下一阶段", 
                 use_container_width=True,
                 disabled=is_disabled,
                 key="next_phase_button"):
        with st.session_state.game_lock:
            st.session_state.phase_progress = Queue()
            
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
                finally:
                    progress_queue.put("done")
            
            st.session_state.phase_thread = Thread(
                target=run_phase,
                args=(st.session_state.phase_progress,)
            )
            st.session_state.phase_thread.start()
    
    # 实时日志更新
    def update_logs():
        if not st.session_state.game:
            return
        
        try:
            current_logs = Context.contexts.get(game, [])
            new_logs = current_logs[len(st.session_state.log_cache):]
            
            time.sleep(2)
            st.rerun()  # 保持强制刷新
            
        except Exception as e:
            st.error(f"日志更新失败: {str(e)}")
    
    # 流式更新监控
    if game.streamlit_log_trigger.is_set():
        update_logs()
        game.streamlit_log_trigger.clear()
    
    # 阶段处理监控
    if st.session_state.phase_thread and st.session_state.phase_thread.is_alive():
        with st.spinner("正在处理游戏阶段..."):
            while True:
                try:
                    if st.session_state.phase_progress.get_nowait() == "done":
                        break
                except:
                    pass
                update_logs()
                time.sleep(0.3)
            
            st.session_state.phase_thread.join()
            update_logs()
            
            if game.game_over():
                st.balloons()
                st.success("🎉 游戏结束！")
                st.session_state.phase_thread = None
                st.session_state.phase_progress = None
                st.stop()

else:
    st.info("👋 请先在侧边栏上传配置文件并初始化游戏")

# 全局样式
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: #f8f9fa !important;
        border-right: 1px solid #eee !important;
    }
    .stButton button {
        transition: all 0.3s ease;
        background: #4a90e2 !important;
        color: white !important;
    }
    .stButton button:disabled {
        background: #cccccc !important;
        cursor: not-allowed;
    }
    .st-emotion-cache-1y4p8pa {
        padding-top: 2rem;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .streaming-message {
        animation: fadeIn 0.5s ease-in;
    }
</style>
""", unsafe_allow_html=True)