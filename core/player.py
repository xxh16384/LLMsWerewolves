from time import sleep
from .context import Context
from core.general import *


class Player:
    def __init__(self, role: str, id: int, using_preset: str, game):
        """初始化一个玩家实例。

        Args:
            role (str): 分配给玩家的角色，如 'werewolf', 'villager' 等。
            id (int): 玩家的唯一数字标识。
            using_preset (str): 玩家使用的预设配置名称，用于查找API信息。
            game (Game): 玩家所属的游戏实例。
        """
        self.game = game
        self.using_preset = using_preset
        self.client = game.clients[self.using_preset]
        self.role = role
        self.id = id
        self.alive = True
        self.recognition = ""
        self.messages = []
        self.init_role_special()
        game.players.append(self)

    def init_system_prompt(self):
        """根据玩家的角色和游戏设置，初始化系统提示信息。

        此方法为大型语言模型构建一条初始指令，告知其扮演的角色、身份号码
        以及游戏规则。对于特殊角色（如狼人），还会提供额外信息（如队友号码）。
        生成的提示信息会作为第一条系统消息存入玩家的消息列表。
        """
        pre_instruction = f"你是{self.id}号玩家，" + self.game.instructions[self.role]
        if self.role == "werewolf":
            wolfs = self.game.get_players("id", alive=False, role="werewolf")
            pre_instruction += f"\n以下玩家是狼人{str(wolfs)[1:-1]}，是你和你的队友"
        self.messages.append({"role": "system", "content": pre_instruction})

    def pub_chat(self, source_id: int, content: str):
        """处理并响应一则公共聊天消息。

        此方法用于玩家在公共频道发言。它会将发言内容和来源信息
        传递给核心的响应生成函数，并设定为公开模式。

        Args:
            source_id (int): 发言者的ID。如果为0，代表是系统（上帝）发言。
            content (str): 发言的具体内容。
        """
        Context(
            self.game, source_id, content, self.game.get_players(t="id", alive=False)
        )
        if source_id == 0:
            self.get_response(f"上帝：{content}", True)
        else:
            self.get_response(f"{source_id}号玩家：{content}", True)

    def private_chat(self, source_id: int, content: str):
        """处理并响应一则私人聊天消息。

        此方法用于玩家接收并回应一则私密消息（通常来自系统）。
        它会将消息内容和来源信息传递给核心的响应生成函数，并设定为私密模式。

        Args:
            source_id (int): 消息来源的ID。通常为0，代表系统（上帝）。
            content (str): 消息的具体内容。
        """
        if source_id == 0:
            Context(self.game, 0, f"{content}", [self.id])
            self.get_response(f"上帝：{content}", False)
        else:
            Context(self.game, source_id, f"{content}", [self.id])
            if not self.game.webui_mode:
                print(f"{source_id}号玩家：{content}")
            self.get_response(f"{source_id}号玩家：{content}", False)

    def get_response(self, prompt: str, if_pub: bool):
        """根据提示生成并处理玩家的响应。

        此函数是玩家与AI模型交互的核心。它会整合历史消息和当前提示，
        构建完整的上下文，然后调用AI模型的API来获取响应。函数还能处理
        流式输出和特殊的思考过程（<think>标签）。最终，生成的响应会被
        记录到游戏上下文中。

        Args:
            prompt (str): 对玩家的当前提示或问题。
            if_pub (bool): 一个布尔值，指示当前是否为公共发言阶段。
                True表示公共，False表示私聊。
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
            model=self.game.apis[self.using_preset]["model_name"],
            messages=message_and_time,
            stream=True,
        )
        self.messages[-1]["content"] = prompt0

        collected_messages = ""
        reasoning_messages = ""
        reasoning_model = -1
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
        collected_messages = (
            "<think>" + reasoning_messages + "</think>" + collected_messages
            if reasoning_messages
            else collected_messages
        )
        Context(self.game, self.id, collected_messages, visible_ids)

        self.messages.append({"role": "assistant", "content": collected_messages})

    def init_role_special(self):
        """根据角色初始化特殊属性。

        这是一个辅助函数，在玩家对象初始化时被调用。
        它会检查玩家的角色，并根据角色赋予其特殊的初始状态。
        例如，为'女巫'角色设置毒药和解药的初始拥有状态。
        """
        if self.role == "witch":
            self.poison = True
            self.antidote = True

    def __str__(self) -> str:
        """返回玩家对象的字符串表示形式。

        Returns:
            str: 一个描述玩家ID和角色的字符串，例如 "玩家5（女巫）"。
        """
        return f"玩家{self.id}（{PLAYERDIC[self.role]}）"
