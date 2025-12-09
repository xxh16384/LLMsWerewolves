import re


class Context:
    contexts = {}
    def __init__(self,game,source_id,content,visible_ids = [],is_streaming = False, last_block = False):
        """
        保存游戏中的一个信息

        Args:
            game (Game): 游戏对象
            source_id (int): 信息的来源id
            content (str): 信息的内容
            visible_ids (list, optional): 可以看到这个信息的玩家id列表. Defaults to [].
        """

        if game not in Context.contexts.keys():
            Context.contexts[game] = []
        
        streaming = False if last_block else True
        if is_streaming:
            pre_block = Context.contexts[game][-1]
            if pre_block.source_id == source_id and pre_block.is_streaming and not pre_block.last_block:
                # 说明和前一条是一个人说的，则更新最后一条
                content = pre_block.content + content
                Context.contexts[game].pop(-1)
        Context.contexts[game].append(self)
        self.game = game
        self.stage = game.stage
        self.is_streaming = is_streaming
        self.last_block = last_block
        self.source_id = source_id
        self.content = content
        self.visible_ids = set(visible_ids + [source_id,0] if visible_ids else [source_id,0])

        if self.game:
            if not streaming:
                self.game.logger.info(self.__str__())
            # 强制触发日志更新（关键改进点）
            if hasattr(self.game, 'streamlit_log_trigger'):
                self.game.streamlit_log_trigger.set()

    def get_context(id,game):
        """
        根据玩家id和游戏id，返回该玩家可以看到的所有信息

        Args:
            id (int): 玩家id
            game (int): 游戏id

        Returns:
            list: 该玩家可以看到的所有信息
        """
        pub_messages = []
        for i in Context.contexts[game]:
            if id in i.visible_ids: #自己可见的
                pub_messages.append(re.sub(r'<think>.*?</think>', '', str(i), flags=re.DOTALL))
        return pub_messages
    
    def get_chat_log(game, stage):
        """
        根据游戏id和阶段，返回该阶段所有信息

        Args:
            game (int/str): 游戏唯一标识符，用于从上下文中获取对应游戏的记录
            stage (int/str): 需要过滤的特定阶段标识符

        Returns:
            list: 包含所有符合条件消息对象的列表，若无匹配项则返回空列表
        """
        messages = []
        # 遍历指定游戏的全部上下文记录
        for i in Context.contexts[game]:
            # 筛选出阶段标识匹配的记录
            if i.stage == stage:
                messages.append(i)
        return messages

    def __str__(self):
        v_id = self.visible_ids
        v_id.discard(0)
        if self.source_id == 0:
            return f"上帝:{self.content}（{v_id}可见）\n"
        return f"{self.source_id}号玩家:{self.content}（{v_id}可见）\n"