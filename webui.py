import streamlit as st
from main import auto, init_game, read_json, get_players, Context, Player,get_players_by_ids
from main import logger, instructions_path, apis_path, players_info_path
import logging
import os

def init_session():
    if "game_initialized" not in st.session_state:
        st.session_state.game_initialized = False
    if "context_messages" not in st.session_state:
        st.session_state.context_messages = []
    if "players" not in st.session_state:
        st.session_state.players = []

def setup_game():
    global apis
    global pre_instructions
    global game_name
    global logger
    
    st.title("AI狼人杀游戏控制器")
    
    with st.sidebar:
        st.header("游戏配置")
        game_name = st.text_input("游戏名称", "default_game")
        instructions_file = st.file_uploader("上传指令文件(instructions.json)", type="json")
        apis_file = st.file_uploader("上传API配置(apis.json)", type="json")
        players_file = st.file_uploader("上传玩家配置(player_info.json)", type="json")

        if st.button("初始化游戏"):
            try:
                # 保存并加载全局配置
                st.session_state.players = []
                for file, name in [(instructions_file, "instructions.json"),
                                 (apis_file, "apis.json"),
                                 (players_file, "player_info.json")]:
                    if file is not None:
                        with open(name, "wb") as f:
                            f.write(file.getbuffer())

                apis = read_json("apis.json")
                pre_instructions = read_json("instructions.json")
                
                players_info = read_json("player_info.json")
                init_game(players_info, apis, pre_instructions)
            
                
                # 初始化session状态
                st.session_state.players = Player.players
                st.session_state.game_initialized = True
                st.success("游戏初始化成功！")
                
            except Exception as e:
                st.error(f"初始化失败: {str(e)}")

def display_game():
    st.header("游戏控制")
    
    # 显示存活玩家
    alive_players = [p for p in st.session_state.players if p.alive]
    dead_players = [p for p in st.session_state.players if not p.alive]
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("存活玩家")
        for p in alive_players:
            st.write(f"玩家{p.id}号 ({p.role})")
    
    with col2:
        st.subheader("出局玩家")
        for p in dead_players:
            st.write(f"玩家{p.id}号 ({p.role})")

    # 操作面板
    st.subheader("游戏操作")
    action = st.selectbox("选择操作", 
                        ["自动进行", "发送公告", "私聊玩家", "公开讨论", "进行投票", "狼人杀人","手动出局", "查看日志"])
    
    if action == "发送公告":
        with st.form("broadcast_form"):
            message = st.text_input("公告内容")
            if st.form_submit_button("发送"):
                Context(0, message, [p.id for p in st.session_state.players])
                st.session_state.context_messages.append(f"系统公告: {message}")
                st.rerun()
    
    elif action == "私聊玩家":
        with st.form("private_chat_form"):
            player_id = st.number_input("玩家编号", min_value=0)
            message = st.text_input("私聊内容")
            if st.form_submit_button("发送"):
                target = next((p for p in st.session_state.players if p.id == player_id), None)
                if target:
                    target.private_chat(0, message)
                    st.session_state.context_messages.append(f"私聊给{player_id}: {message}")
                    st.rerun()
    
    elif action == "手动出局":
        with st.form("out_form"):
            input_str = st.text_input("请输入出局玩家编号（多个用逗号分隔）")
            if st.form_submit_button("确认出局"):
                try:
                    # 解析输入
                    ids = [int(i.strip()) for i in input_str.split(",") if i.strip().isdigit()]
                    
                    # 获取玩家对象
                    players_pending = get_players_by_ids(ids)
                    
                    # 执行出局操作
                    for p in players_pending:
                        p.alive = False
                        Context(0, f"{p.id}号玩家被手动出局", get_players(t="id", alive=False))
                    
                    # 刷新界面
                    st.success(f"已出局玩家: {[p.id for p in players_pending]}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"操作失败: {str(e)}")
    
    elif action == "自动进行":
        pass
        if st.button("开始自动运行"):
            try:
                auto()
                st.session_state.context_messages = [str(ctx) for ctx in Context.contexts]
                st.rerun()
            except Exception as e:
                st.error(f"运行出错: {str(e)}")
    
    # 显示上下文日志
    st.subheader("游戏日志")
    log_container = st.container()
    with log_container:
        for msg in Context.contexts[-20:]:  # 显示最近20条
            st.markdown(f"`{str(msg).strip()}`")

def main():
    init_session()
    setup_game()

    if st.session_state.game_initialized:
        display_game()

if __name__ == "__main__":
    main()