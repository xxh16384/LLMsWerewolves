from time import sleep
from .context import Context
from core.general import *


class Player:
    def __init__(self, role: str, id: int, game):
        """
        使用给定的模型、角色、ID和游戏上下文初始化Player实例。

        参数:
            model (str): 用于玩家的模型标识符，对应API配置。
            role (str): 分配给玩家的游戏角色（例如，狼人、村民、女巫）。
            id (int): 玩家的唯一标识符。
            game: 玩家参与的游戏上下文。

        属性:
            game: 初始化期间传递的游戏上下文。
            client: 使用玩家模型配置的OpenAI客户端实例。
            role (str): 玩家在游戏中的角色。
            id (int): 玩家的唯一标识符。
            model (str): 用于玩家的模型标识符。
            alive (bool): 标志玩家当前是否存活（默认为True）。
            messages (list): 与玩家关联的消息列表。
            poison (bool): 标志女巫角色是否有毒药可用（默认为False）。
            antidote (bool): 标志女巫角色是否有解药可用（默认为False）。
        """

        self.game = game
        # self.client = OpenAI(api_key = game.apis["Model abbreviation"]["api_key"], base_url = game.apis["Model abbreviation"]["base_url"])
        self.client = game.client
        self.role = role
        self.id = id
        self.alive = True

        self.recognition = ""  # 当前是第几天的什么阶段

        self.messages = []
        self.init_role_special()
        game.players.append(self)

    def init_role_special(self):
        if self.role == "witch":
            self.poison = False
            self.antidote = False

    def init_system_prompt(self):
        """
        基于玩家角色和游戏上下文初始化系统提示。

        此方法为玩家构建预指令消息，指示他们在游戏中的角色以及与其角色相关的任何相关信息。
        如果玩家的角色是"werewolf"(狼人)，则会包含其他狼人玩家的额外信息。

        构建的消息作为系统消息追加到玩家的消息列表中。

        副作用:
            使用包含角色特定指令和信息的新系统消息更新玩家的消息列表。

        属性:
            pre_instruction (str): 为玩家构建的指令消息。
            wolfs (list): 非存活的狼人玩家列表，用于为"werewolf"(狼人)角色的玩家提供额外信息。
        """

        pre_instruction = f"你是{self.id}号玩家，" + self.game.instructions[self.role]
        if self.role == "werewolf":
            wolfs = self.game.get_players("id", alive=False, role="werewolf")
            pre_instruction += f"\n以下玩家是狼人{str(wolfs)[1:-1]}，是你和你的队友"
        self.messages.append({"role": "system", "content": pre_instruction})

    def get_response(self, prompt, if_pub):
        """
        在给定提示和响应是否应公开的情况下，模拟与玩家的对话。

        此方法用于在游戏的夜晚和白天阶段都获得玩家的响应。
        当响应应该公开时，在要求玩家回应之前，会向玩家显示所有公开可用的消息。
        当响应不应该公开时，会向玩家显示他们能看到的所有消息，但他们的响应不会与其他玩家共享。

        玩家的响应作为新消息追加到游戏上下文中，并且此方法也会返回该响应。

        参数:
            prompt (str): 给玩家的提示，用作AI模型的输入。
            if_pub (bool): 响应是否应该公开(True)或私密(False)。

        返回:
            str: 玩家对提示的响应。

        副作用:
            玩家的响应作为新消息追加到游戏上下文中。
        """

        sleep(1)

        visible_ids = (
            self.game.get_players("id", alive=False)
            if if_pub
            else [self.id, 0] + self.game.get_players("id", role=self.role)
        )
        pub_messages = Context.get_context(self.id, self.game)
        prompt0 = prompt
        if if_pub:
            prompt = (
                f"\n此前你能得知的玩家发言以及公共信息如下：{str(pub_messages)}...注意：你现在在公共发言阶段，你的所有输出会被所有玩家听到，请直接口语化的输出你想表达的信息，不要暴露你的意图。（连括号中的内容也会被看到）"
                + prompt
            )
        else:
            prompt = (
                f"\n此前你能得知的玩家发言以及公共信息如下：{str(pub_messages)}...注意：你现在在私聊阶段，你的输出只会被上帝听到。（如果你是狼人，你的聊天还会被同阵营的玩家听到）"
                + prompt
            )

        self.messages.append({"role": "user", "content": prompt})

        message_and_time = self.messages.copy()

        message_and_time.append({"role": "system", "content": f"现在是{self.game}。"})

        print(f"{self} 的上下文： {message_and_time}")

        response = self.client.chat.completions.create(
            model=self.game.apis["Model abbreviation"]["model_name"],
            messages=message_and_time,
            stream=True,
        )
        self.messages[-1]["content"] = prompt0

        # 处理回复
        collected_messages = ""
        reasoning_messages = ""
        reasoning_model = -1  # 判断是否是推理模型，-1待判断，0不是，1是
        print(f"玩家{self.id}（{self.role}）： ", end="", flush=True)
        for chunk in response:
            if reasoning_model == -1:
                try:
                    reasoning_message = chunk.choices[0].delta.reasoning_content
                    reasoning_messages += reasoning_message
                    reasoning_model = 1
                    reasoning = True
                    print("思考中...\n", end="", flush=True)
                    print(reasoning_message, end="", flush=True)
                except:
                    reasoning_model = 0
                    chunk_message = chunk.choices[0].delta.content
                    collected_messages += chunk_message
                    print(chunk_message, end="", flush=True)
            elif reasoning_model == 1:
                reasoning_message = chunk.choices[0].delta.reasoning_content
                chunk_message = chunk.choices[0].delta.content
                if reasoning_message and reasoning:
                    reasoning_messages += reasoning_message
                    print(reasoning_message, end="", flush=True)
                elif not reasoning_message and reasoning and chunk_message:
                    print("\n思考结束...\n")
                    reasoning = False
                    collected_messages += chunk_message
                    print(chunk_message, end="", flush=True)
                elif not reasoning:
                    collected_messages += chunk_message
                    print(chunk_message, end="", flush=True)
            else:
                chunk_message = chunk.choices[0].delta.content
                collected_messages += chunk_message
                print(chunk_message, end="", flush=True)

        print("")
        # 加入公共上下文
        collected_messages = (
            "<think>" + reasoning_messages + "</think>" + collected_messages
            if reasoning_messages
            else collected_messages
        )
        Context(self.game, self.id, collected_messages, visible_ids)

        self.messages.append({"role": "assistant", "content": collected_messages})

    def private_chat(self, source_id, content):
        """
        允许玩家向另一个玩家发送私人聊天消息。

        参数:
            source_id (int): 发送消息的玩家ID。
            content (str): 要发送的聊天消息内容。
        """

        if source_id == 0:
            Context(self.game, 0, f"{content}", [self.id])
            # if not self.game.webui_mode:
            #     print(f"上帝：{content}")
            self.get_response(f"上帝：{content}", False)
        else:
            Context(self.game, source_id, f"{content}", [self.id])
            if not self.game.webui_mode:
                print(f"{source_id}号玩家：{content}")
            self.get_response(f"{source_id}号玩家：{content}", False)

    def pub_chat(self, source_id, content):
        """
        处理游戏上下文中的公共聊天消息。

        此方法允许玩家或系统（由source_id = 0表示）向所有玩家发送公共聊天消息。
        消息被处理并公开显示，让所有玩家都能看到互动。

        参数:
            source_id (int): 发送消息的玩家或系统的ID。
                            如果为0，则消息来自系统("上帝")。
            content (str): 要公开发送的消息内容。
        """

        Context(
            self.game, source_id, content, self.game.get_player(t="id", alive=False)
        )
        if source_id == 0:
            self.get_response(f"上帝：{content}", True)
        else:
            self.get_response(f"{source_id}号玩家：{content}", True)

    def __str__(self):
        return f"玩家{self.id}（{PLAYERDIC[self.role]}）"
