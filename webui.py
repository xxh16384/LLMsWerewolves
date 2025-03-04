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

ROLE_ICONS = {
    "werewolf": "🐺",
    "villager": "👨🌾",
    "witch": "🧙♀",
    "seer": "🔮"
}

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
    {streaming_style}
'>
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 1.2em">{ROLE_ICONS.get(role, "")}</span>
        <strong>玩家 {context.source_id} ({role})</strong>
    </div>
    <div style='margin-top: 8px;'>
        {context.content.replace('\n', '<br>')}
    </div>
</div>"""

# 侧边栏配置
with st.sidebar:
    st.title("⚙️ 游戏配置")
    
    # 文件上传
    uploaded_files = {
        'player_info': st.file_uploader("玩家配置 (player_info.json)", type="json"),
        'apis': st.file_uploader("API配置 (apis.json)", type="json"),
        'instructions': st.file_uploader("游戏指令 (instructions.json)", type="json")
    }
    
    game_name = st.text_input("游戏名称", "狼人杀游戏1")
    
    if st.button("🔄 初始化游戏", use_container_width=True):
        if all(uploaded_files.values()):
            try:
                configs = {}
                for key, uploader in uploaded_files.items():
                    configs[key] = json.load(uploader)
                
                with st.spinner("正在创建游戏..."):
                    with st.session_state.game_lock:
                        st.session_state.game = Game(
                            game_name,
                            players_info_path=configs['player_info'],
                            apis_path=configs['apis'],
                            instructions_path=configs['instructions'],
                            is_webui_mode=True
                        )
                        st.session_state.game.is_webui_mode = True  # 启用WebUI模式
                        st.session_state.game.streamlit_log_trigger = Event()
                        st.session_state.log_cache = []
                        st.session_state.phase_thread = None
                        st.session_state.phase_progress = None
                        st.session_state.log_container = st.empty()
                        st.success("游戏初始化成功！")
            except Exception as e:
                st.error(f"配置错误: {str(e)}")
        else:
            st.warning("请先上传所有配置文件")

# 主界面
st.title("🎭 狼人杀AI对局系统")

# 玩家状态栏
if st.session_state.game:
    st.subheader("👥 玩家状态")
    players = st.session_state.game.get_players(alive=False)
    
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
            
            # 动态更新日志
            with st.session_state.log_container.container():
                for ctx in new_logs:
                    st.markdown(format_log_message(ctx, game), unsafe_allow_html=True)
                
                # 强制刷新界面
                st.rerun()
                
            st.session_state.log_cache = current_logs.copy()
            
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