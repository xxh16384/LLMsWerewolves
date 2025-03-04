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
    "seer": "预言家"
}

# 初始化session状态（确保在主线程初始化）
def init_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.game = None
        st.session_state.log_cache = []
        st.session_state.game_lock = Lock()
        st.session_state.phase_thread = None
        st.session_state.phase_progress = None  # 初始化为None
        st.session_state.initialized = True

init_session_state()

def format_log_message(context, game):
    role = "上帝" if context.source_id == 0 else next(
        (p.role for p in game.players if p.id == context.source_id), "未知"
    )
    
    # 使用标准颜色代码并修复闭合标签
    return f"""
<div style='
    padding: 10px;
    margin: 8px 0;
    border-radius: 8px;
    background-color: {ROLE_COLORS.get(role, "#F0F0F0")};
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
'>
    <strong style='font-size: 0.9em;'>{role} (玩家{context.source_id})</strong>
    <div style='margin-top: 5px; font-size: 0.95em;'>
        {context.content.replace('\n', '<br>')}
    </div>
</div>
    """  # 显式闭合div标签 <source_id data="webui.py" />

# 主界面
st.title("狼人杀大模型版")

# 侧边栏控制
with st.sidebar:
    st.title("游戏控制台")
    game_name = st.text_input("输入游戏名称", "狼人杀游戏1")
    
    if st.button("创建新游戏"):
        with st.spinner("初始化游戏..."), st.session_state.game_lock:
            st.session_state.game = None
            st.session_state.log_cache = []
            st.session_state.phase_thread = None
            st.session_state.phase_progress = None  # 重置为None
            st.session_state.initialized = False
            
            st.session_state.game = Game(
                game_name,
                "player_info.json",
                "apis.json",
                "instructions.json"
            )
            st.session_state.initialized = True
            st.success(f"游戏 {game_name} 创建成功！")

if st.session_state.game and st.session_state.initialized:
    game = st.session_state.game
    
    log_container = st.empty()
    
    st.subheader("存活玩家状态")
    players = game.get_players(alive=False)
    cols = st.columns(3)
    for i, player in enumerate(players):
        with cols[i % 3]:
            role_color = ROLE_COLORS.get(player.role, "#FFF")
            st.markdown(f"""
<div style='text-align: center; padding: 12px; border-radius: 12px; background-color: {role_color};'>
    <h4>玩家{player.id}</h4>
    <p>{player_role_to_chinese[player.role]}</p>
    <p>{'✅ 存活' if player.alive else '❌ 出局'}</p>
</div>
            """, unsafe_allow_html=True)
    
    def update_logs():
        current_logs = Context.contexts.get(game, [])
        new_logs = current_logs[len(st.session_state.log_cache):]
        
        # 添加空内容检测 <source_id data="webui.py" />
        if not new_logs and not st.session_state.log_cache:
            log_container.markdown("暂无日志", unsafe_allow_html=True)
            return
        
        # 强制转换为字符串避免对象类型问题
        formatted_logs = "".join([str(format_log_message(c, game)) for c in st.session_state.log_cache + new_logs])
        
        # 使用固定高度容器并添加边界
        log_container.markdown(f"""
<div style='
    max-height: 500px; 
    overflow-y: auto;
    padding: 15px;
    border: 2px solid #4A90E2;
    border-radius: 10px;
    background-color: #F8F9FA;
    margin-bottom: 20px;
'>
    {formatted_logs}
</div>
        """, unsafe_allow_html=True)  # 必须保留参数 <source_id data="webui.py" />
        
        st.session_state.log_cache = current_logs.copy()
        
        # 生成带自动滚动脚本的HTML
        scroll_script = """
<script>
    // 强制滚动到底部
    function scrollToBottom() {
        var logContainer = document.getElementById('log-container');
        if(logContainer) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }
    // DOM加载后执行 + 200ms延迟确保渲染完成
    document.addEventListener("DOMContentLoaded", function(){ 
        setTimeout(scrollToBottom, 200)
    });
    // 额外触发一次防止异步加载问题
    window.addEventListener('load', scrollToBottom);
</script>
        """

        log_container.markdown(f"""
<div id="log-container" style='
    max-height: 500px;
    overflow-y: auto;
    padding: 15px;
    border: 2px solid #4A90E2;
    border-radius: 10px;
'>
    {formatted_logs}
</div>
{scroll_script}
        """, unsafe_allow_html=True)  # <source_id data="webui.py" />
    
    days, phase = game.get_game_stage()
    st.info(f"当前阶段：第{days}天 {'☀️ 白天' if phase else '🌙 夜晚'}")
    
    if st.button("进入下一阶段"):
        with st.spinner("处理阶段..."), st.session_state.game_lock:
            if st.session_state.phase_thread and st.session_state.phase_thread.is_alive():
                if st.session_state.phase_progress:
                    st.session_state.phase_progress.put("skip")
                st.session_state.phase_thread.join(timeout=2)
            
            # 创建新的队列并传递给线程
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
                finally:
                    progress_queue.put("done")
            
            st.session_state.phase_thread = Thread(target=run_phase, args=(phase_progress,))
            st.session_state.phase_thread.start()
    
    def monitor_phase(progress_queue):
        start_time = time.time()
        while time.time() - start_time < 30:
            with st.session_state.game_lock:  # 添加线程锁 <source_id data="webui.py" />
                update_logs()
            
            # 增强刷新频率
            time.sleep(0.5)
            st.rerun()  # 强制界面刷新
            
            try:
                if progress_queue.get_nowait() == "done":
                    break
            except:
                continue
            st.components.v1.html(
            """
            <script>
                var logDiv = document.getElementById('log-container');
                if(logDiv) logDiv.scrollTop = logDiv.scrollHeight;
            </script>
            """,
            height=0
        )  # <source_id data="webui.py" />
    
    if st.session_state.phase_thread and st.session_state.phase_thread.is_alive():
        with st.spinner("阶段处理中..."):
            if st.session_state.phase_progress:
                monitor_phase(st.session_state.phase_progress)
        
        if game.game_over():
            st.balloons()
            st.success("游戏结束！")
            st.stop()
    else:
        update_logs()
else:
    st.info("请先创建游戏")