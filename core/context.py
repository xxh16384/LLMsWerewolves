import re


class Context:
    contexts = {}

    def __init__(
        self,
        game,
        source_id: str,
        content: str,
        visible_ids: list = [],
        is_streaming: bool = False,
        last_block: bool = False,
    ):
        """初始化并记录一个新的游戏上下文（信息）实例。

        此构造函数负责创建一个新的信息单元，并将其添加到对应游戏的全局上下文中。
        它还处理流式消息的合并，并根据可见性规则设置信息的受众。

        Args:
            game (Game): 信息所属的游戏实例。
            source_id (int): 信息的来源ID（0通常代表系统或“上帝”）。
            content (str): 信息的主要内容。
            visible_ids (list, optional): 一个列表，包含可以看到此信息的玩家ID。
                默认为空列表。
            is_streaming (bool, optional): 标记此信息是否为流式传输的一部分。
                默认为 False。
            last_block (bool, optional): 当 is_streaming 为 True 时，标记这是否是
                流式传输的最后一个数据块。默认为 False。
        """
        if game not in Context.contexts.keys():
            Context.contexts[game] = []

        streaming = False if last_block else True
        if is_streaming:
            pre_block = Context.contexts[game][-1]
            if (
                pre_block.source_id == source_id
                and pre_block.is_streaming
                and not pre_block.last_block
            ):
                content = pre_block.content + content
                Context.contexts[game].pop(-1)

        Context.contexts[game].append(self)
        self.game = game
        self.stage = game.stage
        self.is_streaming = is_streaming
        self.last_block = last_block
        self.source_id = source_id
        content = f"【此信息被发出的时间:{game}，" + content + "】"
        self.content = content
        self.visible_ids = set(
            visible_ids + [source_id, 0] if visible_ids else [source_id, 0]
        )

        if self.game:
            if not streaming:
                self.game.logger.info(self.__str__())
            if hasattr(self.game, "streamlit_log_trigger"):
                self.game.streamlit_log_trigger.set()

    @staticmethod
    def get_context(ids: int, game) -> list:
        """获取指定玩家在特定游戏中可见的所有信息。

        此静态方法遍历指定游戏的所有上下文记录，筛选出对特定玩家ID可见
        的信息，并将其格式化为字符串列表返回。它会自动过滤掉用于AI思考
        的`<think>`标签内容。

        Args:
            ids (int): 玩家的ID。
            game (Game): 需要查询的游戏实例。

        Returns:
            list: 一个字符串列表，其中每个字符串都是一条对该玩家可见的格式化信息。
        """
        pub_messages = []
        for i in Context.contexts[game]:
            if ids in i.visible_ids:
                pub_messages.append(
                    re.sub(r"<think>.*?</think>", "", str(i), flags=re.DOTALL)
                )
        return pub_messages

    @staticmethod
    def get_chat_log(game, stage: int) -> list:
        """获取特定游戏在指定阶段的所有聊天记录。

        此静态方法用于从全局上下文中筛选出属于特定游戏和特定阶段的所有
        信息对象。

        Args:
            game (Game): 需要查询的游戏实例。
            stage (int): 需要筛选的游戏阶段编号。

        Returns:
            list: 一个包含所有匹配阶段的 `Context` 对象的列表。
        """
        messages = []
        for i in Context.contexts[game]:
            if i.stage == stage:
                messages.append(i)
        return messages

    def __str__(self) -> str:
        """返回该上下文信息的可读字符串表示形式。

        格式为“来源: 内容（可见范围）”。

        Returns:
            str: 格式化后的信息字符串。
        """
        v_id = self.visible_ids.copy()
        v_id.discard(0)
        if self.source_id == 0:
            return f"上帝:{self.content}（{v_id}可见）\n"
        return f"{self.source_id}号玩家:{self.content}（{v_id}可见）\n"
