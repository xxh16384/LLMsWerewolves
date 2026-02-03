# core/player.py


from time import sleep
from .context import Context
from .io import cur_io
from .general import *


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
            wolfs = self.game.get_players_by_factions(t="id", faction="bad")
            wolfs.remove(self.id)
            pre_instruction += f"\n以下玩家是你的队友，他们也是狼人：{str(wolfs)}。"
        elif self.role == "whitewolf":
            wolfs = self.game.get_players_by_factions(t="id", faction="bad")
            wolfs.remove(self.id)
            pre_instruction += f"\n以下玩家是狼人，是你的暂时队友，在游戏发展中，你可以选择背叛他们以博取单人胜利：{str(wolfs)}。"
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

    def private_chat(self, source_id: int, content: str, faction: bool = False):
        """处理并响应一则私人聊天消息。

        此方法用于玩家接收并回应一则私密消息（通常来自系统）。
        它会将消息内容和来源信息传递给核心的响应生成函数，并设定为私密模式。

        Args:
            source_id (int): 消息来源的ID。通常为0，代表系统（上帝）。
            content (str): 消息的具体内容。
            faction (bool, optional): 一个布尔值，指示是否给所有同阵营的发布信息。
                True表示发布，False表示不发布。
        """
        if source_id == 0:
            Context(self.game, 0, f"{content}", [self.id])
            self.get_response(f"上帝：{content}", False, if_faction=faction)
        else:
            Context(self.game, source_id, f"{content}", [self.id])
            if not self.game.webui_mode:
                cur_io.IO_output(f"{source_id}号玩家：{content}")
            self.get_response(
                f"{source_id}号玩家：{content}", False, if_faction=faction
            )

    def get_response(
        self,
        prompt: str,
        if_pub: bool = False,
        if_faction: bool = False,
        if_self: bool = True,
    ):
        """根据提示生成并处理玩家的响应。

        此函数是玩家与AI模型交互的核心。它会整合历史消息和当前提示，
        构建完整的上下文，然后调用AI模型的API来获取响应。函数还能处理
        流式输出和特殊的思考过程（<think>标签）。最终，生成的响应会被
        记录到游戏上下文中。

        Args:
            prompt (str): 对玩家的当前提示或问题。
            if_pub (bool, optional): 一个布尔值，指示当前是否为公共发言阶段。
                True表示公共，False表示私聊。
            if_faction (bool, optional): 一个布尔值，指示是否给所有同阵营的发布信息。
                True表示发布，False表示不发布。
            if_self (bool, optional): 一个布尔值，指示是否给所有同阵营的发布信息。
                True表示发布，False表示不发布。
        """

        def get_visibles():
            # 获取“这个信息的可见对象”的列表
            if if_pub:
                visible_ids = self.game.get_players("id", alive=False)
            elif if_faction:
                visible_ids = [self.id, 0] + self.game.get_players_by_factions(
                    "id", faction=LEGAL_ROLE[self.role]
                )
            elif if_self:
                visible_ids = [self.id, 0] + self.game.get_players("id", role=self.role)
            else:
                visible_ids = [self.id, 0]
            return visible_ids

        def get_prompts():
            # 获取将要发送给AI的信息

            # 获取所有对该player公开的消息
            pub_messages = Context.get_context(self.id, self.game)
            # 将这段对话单独存入AI的上下文中
            self.messages.append({"role": "user", "content": prompt})
            # 单独拉一个上下文出来
            message_and_time = self.messages.copy()

            if if_pub:
                system_prompt = f"\n此前你能得知的玩家发言以及公共信息如下：{str(pub_messages)}。注意：你现在在公共发言阶段，你的**所有输出**都会被**所有玩家**听到，此阶段不允许私聊。如果你有想要隐瞒的信息，请不要暴露你的意图，同理，也不要太信任他人在公共频道说的话。你不允许使用任何括号括住你的任何发言。"
            else:
                system_prompt = f"\n此前你能得知的玩家发言以及公共信息如下：{str(pub_messages)}。注意：你现在在私聊阶段，你的输出只会被上帝听到。如果你是狼人，你的聊天还会被同阵营的玩家听到。"

            # 然后在这个单独的上下文中再添加这些想要添加的，只需要给这一段的信息（之前的那个诗山太tm抽象了）
            message_and_time.append(
                {"role": "system", "content": f"现在是{self.game}。{system_prompt}"}
            )
            # cur_io.IO_output(f"{self} 的上下文： {message_and_time}")

            return message_and_time

        def get_model_response(max_times: int = 3):
            times = 0
            response = ""
            while times < max_times:
                try:
                    response = self.client.chat.completions.create(
                        model=self.game.apis[self.using_preset]["model_name"],
                        messages=message_and_time,
                        stream=True,
                    )
                    break
                except Exception as e:
                    times += 1
                    sleep(5)
                    if times == max_times:
                        cur_io.IO_output(
                            f"————————————————————————————————————————报告！报错了！{max_times}次请求都没有请求到API返回！但我没有做处理！所以你最好这里直接把程序关了不然一会还是会报错！————————————————————————————————————————"
                        )
                        cur_io.IO_input(f"报错信息:{type(e).__name__, str(e)}")
            return response

        def get_final_content(response):
            collected_content = []
            collected_reasoning = []
            is_thinking = False  # 标记一下是否在思考
            cur_io.IO_s_output(f"玩家{self.id}（{self.role}）： ")

            for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                reasoning_part = getattr(delta, "reasoning_content", None) or ""
                content_part = getattr(delta, "content", None) or ""
                if reasoning_part:
                    # 检测到在思考
                    if not is_thinking:
                        cur_io.IO_s_output("开始思考...\n")
                        is_thinking = True
                    # 输出思考部分，将思考部分加到结果里去
                    cur_io.IO_s_output(reasoning_part)
                    collected_reasoning.append(reasoning_part)
                elif content_part:
                    # 检测到没在思考
                    if is_thinking:
                        cur_io.IO_s_output("\n思考结束...\n")
                        is_thinking = False
                    # 输出正文部分，将正文部分加到结果里去
                    cur_io.IO_s_output(content_part)
                    collected_content.append(content_part)
            cur_io.IO_output("")

            full_reasoning = "".join(collected_reasoning)  # 说不定会有用
            full_content = "".join(collected_content)

            return full_reasoning, full_content

        sleep(1)

        visible_ids = get_visibles()
        message_and_time = get_prompts()
        response = get_model_response()
        full_reasoning, full_content = get_final_content(response)

        if if_pub:
            full_content = "【公共频道发言】" + full_content

        Context(self.game, self.id, full_content, visible_ids)

        self.messages.append({"role": "assistant", "content": full_content})

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
