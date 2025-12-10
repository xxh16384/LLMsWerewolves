import logging
import os
from time import time
from random import choice
from .tools import read_json, extract_numbers_from_brackets, find_max_key, makeDic
from .context import Context
from .player import Player
from .general import *


class Game:
    def __init__(
        self, game_name, players_info_path, apis_path, instructions_path, roles
    ):
        """
        初始化游戏对象

        参数:
            game_name (str): 游戏名称
            players_info_path (str): 玩家信息文件路径
            apis_path (str): API配置文件路径
            instructions_path (str): 游戏指令文件路径

        返回值:
            无
        """
        self.game_name = game_name
        self.stage = 0
        self.id = time()
        self.set_logger()

        self.instructions = read_json(instructions_path)
        self.apis = read_json(apis_path)
        self.players_info = read_json(players_info_path)

        # self.client = OpenAI(
        #     api_key=self.apis["Model abbreviation"]["api_key"],
        #     base_url=self.apis["Model abbreviation"]["base_url"],
        # )

        self.players = []
        self.roles = roles.copy()

        self.role_prompts = f"\
            这是一局有{len(self.roles)}个玩家的狼人杀游戏，\
                一共有  {self.roles["werewolf"] + "个狼人，" if self.roles["werewolf"] > 0 else ""}\
                        {self.roles["villager"] + "个村民，" if self.roles["villager"] > 0 else ""}\
                        {self.roles["seer"] + "个预言家，" if self.roles["seer"] > 0 else ""}\
                        {self.roles["witch"] + "个女巫，" if self.roles["witch"] > 0 else ""}\
                        {self.roles["guard"] + "个守卫，" if self.roles["guard"] > 0 else ""}"

        self.init_game()

        self.kill_tonight = []
        self.guard_tonight = []

    def set_logger(self):
        """
        设置日志记录器

        该函数负责创建日志目录、配置日志基本信息、创建日志记录器实例，
        并将日志记录器保存到实例变量中。

        参数:
            无

        返回值:
            无返回值

        功能说明:
            1. 检查并创建日志目录
            2. 配置日志基本设置，包括日志级别、格式、输出文件等
            3. 创建指定ID的日志记录器
            4. 输出一条测试性的调试日志
            5. 将日志记录器保存到实例变量中供后续使用
        """
        # 创建文件处理器 (File Handler)
        if not os.path.exists("./log"):
            os.mkdir("./log")

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename=f"./log/{self.game_name}-id={self.id}.md",
            encoding="UTF-8",
        )

        logger = logging.getLogger(str(self.id))

        logger.debug("这是一条调试信息")

        self.logger = logger

    def init_game(self):
        """
        初始化游戏对象

        该函数完成以下初始化工作：
        1. 根据玩家信息创建除主持人外的所有玩家对象
        2. 初始化所有玩家的系统提示信息
        3. 创建游戏上下文环境

        参数:
            无

        返回值:
            无
        """
        for i in self.players_info.keys():
            if i == "0" or i == 0:
                continue
            # roles = self.players_info[i]["role"]
            role = self.give_role()
            preset = self.players_info[i]["preset"]
            Player(role, int(i), preset, self)
        for i in self.players:
            i.init_system_prompt()
        # Context(self, 0, self.players_info["0"], self.get_players(t="id", alive=False))
        Context(self, 0, self.role_prompts, self.get_players(t="id", alive=False))

    def get_players(self, t="object", alive=True, role="all"):
        """
        获取符合条件的玩家列表

        参数:
            t (str): 返回数据类型，"object"返回玩家对象列表，"id"返回玩家ID列表，默认为"object"
            alive (bool): 是否只返回存活的玩家，True表示只返回存活玩家，False表示返回所有玩家，默认为True
            role (str): 玩家角色筛选条件，"all"表示不限制角色，其他值表示指定特定角色，默认为"all"

        返回:
            list: 根据参数条件筛选后的玩家列表，列表元素类型由参数t决定
        """
        if role == "all":
            if alive:
                if t == "object":
                    return [i for i in self.players if i.alive]
                elif t == "id":
                    return [i.id for i in self.players if i.alive]
            else:
                if t == "object":
                    return self.players
                elif t == "id":
                    return [i.id for i in self.players]
        else:
            if alive:
                if t == "object":
                    return [i for i in self.players if i.role == role and i.alive]
                elif t == "id":
                    return [i.id for i in self.players if i.role == role and i.alive]
            else:
                if t == "object":
                    return [i for i in self.players if i.role == role]
                elif t == "id":
                    return [i.id for i in self.players if i.role == role]

    def get_players_by_ids(self, ids: list):
        """
        根据玩家ID列表获取对应的玩家对象列表

        参数:
            ids (list): 包含玩家ID的列表，ID可以是字符串或数字类型

        返回:
            list: 包含匹配的Player对象的列表，如果找不到对应ID的玩家则返回空列表
        """
        ids = [int(i) for i in ids]
        players_pending = [i for i in self.players if i.id in ids]
        return players_pending

    def guard_guarding(self):
        """
        处理守卫角色的保护行动

        该函数负责与守卫玩家交互，获取其保护目标，并记录相关上下文信息。
        守卫可以在夜间选择保护一名玩家，或者选择不保护任何人。

        参数:
            无

        返回值:
            无
        """

        def talk_guard(message: str):
            # 通知守卫消息
            guard.private_chat(0, message)

        def record_guard(message: str):
            # 将消息加入守卫的上下文
            Context(self, 0, message, self.get_players(t="id", role="guard"))

        guard = self.get_players(role="guard")
        if not guard:
            return
        guard = guard[0]

        talk_guard(
            "你今晚要保护谁？要保护的玩家编号请用[]包围，若不保护人则输出[0]，例如'我要保护[7]号玩家'或'我不想保护人，[0]'。可以简短的给出理由。"
        )
        target = extract_numbers_from_brackets(guard.messages[-1]["content"])
        if target and target != 0:
            record_guard(
                f"在{self.get_day}的晚上，你保护了玩家{self.get_players_by_ids(target)[0]}。"
            )
        self.guard_tonight.append(target)

    def werewolf_killing(self):
        """
        狼人杀人阶段的主要逻辑函数

        该函数处理狼人讨论和投票杀人的完整流程，包括：
        1. 通知所有狼人进行讨论
        2. 收集狼人的杀人投票
        3. 统计投票结果并确定被杀目标
        4. 记录杀人意图到游戏上下文

        参数:
            无

        返回值:
            无返回值
        """

        def talk_werewolf(target, message: str):
            target.private_chat(0, message)

        def record_werewolf(message: str):
            # 将消息加入预言家的上下文
            Context(self, 0, message, self.get_players(t="id", role="werewolf"))

        wolves = self.get_players(role="werewolf")

        if not wolves:
            return

        for wolf in wolves:
            talk_werewolf(wolf, "今晚你想杀谁？现在是讨论阶段。")

        for wolf in wolves:
            talk_werewolf(
                wolf,
                "请进行杀人投票，杀人投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以自由发言解释杀人理由。",
            )

        result = makeDic(self.get_players())

        for wolf in wolves:
            ToKilled = extract_numbers_from_brackets(wolf.messages[-1]["content"])
            if ToKilled and int(ToKilled[-1]) in self.get_players("id"):
                result[int(ToKilled[-1])] += 1

        killed = find_max_key(result)
        if killed and killed != 0:
            record_werewolf(f"在{self.get_day}的晚上，{killed}号玩家被狼人标记要杀。")
            if not killed in self.guard_tonight:
                self.kill_tonight.append(killed)
        else:
            record_werewolf(f"在{self.get_day}的晚上，狼人没有选择任何人要杀。")

    def seer_seeing(self):
        """
        处理预言家夜晚查验身份的逻辑流程

        该函数负责：
        1. 获取当前存活的预言家玩家
        2. 向预言家发送查验指令消息
        3. 解析预言家的选择结果
        4. 记录查验结果到游戏上下文

        参数:
            无

        返回值:
            无
        """

        def talk_seer(message: str):
            # 通知预言家消息
            seer.private_chat(0, message)

        def record_seer(message: str):
            # 将消息加入预言家的上下文
            Context(self, 0, message, self.get_players(t="id", role="seer"))

        seer = self.get_players(role="seer")
        if not seer:
            return
        seer = seer[0]
        talk_seer(
            "你今晚要查谁？要查询的玩家编号请用[]包围，例如'我要查询[7]号玩家'。可以简短的给出理由。"
        )
        target = extract_numbers_from_brackets(seer.messages[-1]["content"])
        record_seer(
            f"在{self.get_day}的晚上，你查的玩家是{self.get_players_by_ids(target)[0]}，他的身份是{self.get_players_by_ids(target)[0].role}。"
        )

    def witch_operation(self):
        """
        执行女巫角色的操作逻辑。

        女巫每晚可以执行两个操作：
        1. 使用解药救人（如果当晚有玩家被杀且拥有解药）；
        2. 使用毒药杀人（如果还有毒药可用）。

        此方法会与女巫进行交互，获取其决策，并更新游戏状态。

        参数:
            无

        返回值:
            无
        """

        def talk_witch(message: str):
            # 通知女巫消息
            witch.private_chat(0, message)

        def record_witch(message: str):
            # 将消息加入女巫的上下文
            Context(self, 0, message, self.get_players(t="id", role="witch"))

        witch = self.get_players(role="witch")
        if not witch:
            return

        witch = witch[0]

        # 有人死了，允许救人
        if self.kill_tonight:
            if witch.antidote:
                talk_witch(
                    f"在{self.get_day}的晚上，{self.kill_tonight}号玩家被杀了，你可以选择救他或者不救，选择结果用[]包围，救请写[1]，不救请写[0]，你可以简短的给出理由。"
                )
                cured = extract_numbers_from_brackets(witch.messages[-1]["content"])
                if cured and int(cured[-1]):
                    witch.antidote = True
                    record_witch(
                        f"在{self.get_day}的晚上，{self.kill_tonight[0]}号玩家被杀了，你选择了救他。"
                    )
                    self.kill_tonight.remove(int(cured[-1]))
                    witch.antidote = False
            else:
                record_witch(
                    f"在{self.get_day}的晚上，{self.kill_tonight[0]}号玩家被杀了，但你没有解药，没法救他。"
                )
        # 没人死，不需要救人
        else:
            record_witch(f"在{self.get_day}的晚上，在你的行动阶段之前，没有人死。")

        # 毒杀
        if witch.poison:
            talk_witch(
                f"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。",
            )
            poisoned = extract_numbers_from_brackets(witch.messages[-1]["content"])
            if int(poisoned[-1]):
                witch.poison = True
                record_witch(
                    f"在{self.get_day}的晚上，你选择了毒杀{int(poisoned[-1])}号玩家。"
                )
                self.kill_tonight.append(int(poisoned[-1]))
                witch.poison = False
        else:
            record_witch(f"在{self.get_day}的晚上，你今晚没有毒，所以没有毒杀人。")

    def public_discussion(self):
        """
        进行公共讨论阶段，将起始讨论信息加入每个玩家的上下文并开始顺序发言。

        参数:
            无

        返回值:
            无
        """
        players_pending = self.get_players()
        for player in players_pending:
            player.pub_chat(0, "请公开讨论，在此阶段你可以简短发言，解释讨论理由。")

    def vote(self) -> dict:
        """
        执行投票流程，收集所有玩家的投票并统计结果

        参数：
            无

        返回:
            dict: 投票结果字典，键为玩家ID，值为获得的票数
        """
        players_pending = self.get_players()
        for player in players_pending:
            player.pub_chat(
                0,
                "请投票，投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以简短发言，解释投票理由。",
            )
        result = makeDic(players_pending)
        for i in players_pending:
            voted = extract_numbers_from_brackets(i.messages[-1]["content"])
            if voted and int(voted[-1]) in self.get_players("id"):
                result[int(voted[-1])] += 1
        return result

    def game_over(self) -> int:
        """
        判断游戏是否结束

        返回:
            int: 1表示游戏结束，0表示游戏继续进行
        """

        if (
            len(self.get_players(alive=True))
            - 2 * len(self.get_players(alive=True, role="werewolf"))
            < 0
        ):  # 好人数量小于狼人数量
            return 1
        elif len(self.get_players(alive=True, role="werewolf")) == 0:
            return 1
        else:
            return 0

    def get_winner(self) -> str:
        """
        获取游戏胜利者

        该函数判断游戏的最终胜利者，根据存活玩家中狼人与好人数量的关系来决定胜负。
        当狼人数量占优时狼人获胜，当所有狼人都被淘汰时好人获胜。

        返回:
            str: 返回胜利阵营名称，"狼人"或"好人"
        """
        if self.game_over():
            if (
                len(self.get_players(alive=True))
                - 2 * len(self.get_players(alive=True, role="werewolf"))
                < 0
            ):
                Context(
                    self,
                    0,
                    f"游戏结束，狼人获胜",
                    self.get_players(t="id", alive=False),
                )
                return "狼人"
            elif len(self.get_players(alive=True, role="werewolf")) == 0:
                Context(
                    self,
                    0,
                    f"游戏结束，好人获胜",
                    self.get_players(t="id", alive=False),
                )
                return "好人"

    def broadcast(self, content):
        """
        向所有玩家广播消息

        参数:
            content: 要广播的内容

        返回值:
            无返回值
        """
        Context(self, 0, content, self.get_players(t="id", alive=False))

    def out(self, player_ids: list):
        """
        出局玩家，给定player_ids列表。
        这将直接将给定玩家的存活状态设置为False，
        并向所有玩家广播此消息。

        参数:
            player_ids (list): 玩家ID列表

        返回值:
            无返回值
        """
        if not player_ids:
            self.broadcast("出局失败")
            return
        players_pending = self.get_players_by_ids(player_ids)
        if not players_pending:
            raise ValueError("出局失败")
        for i in players_pending:
            i.alive = False
        self.broadcast(f"{str(player_ids)[1:-1]}号玩家出局")

    def no_out(self, player_ids: list):
        """
        取消玩家出局状态，给定player_ids列表。
        这将直接将给定玩家的存活状态设置为True，
        并向所有玩家广播此消息。

        参数:
            player_ids (list): 玩家ID列表
        """
        if not player_ids:
            self.broadcast("加入失败")
            return
        players_pending = self.get_players_by_ids(player_ids)
        if not players_pending:
            raise ValueError("加入失败")
        for i in players_pending:
            i.alive = True
        self.broadcast(f"{str(player_ids)[1:-1]}号玩家加入")

    def give_role(self):
        new_role = choice(self.roles)
        self.roles.remove(new_role)
        return new_role

    def day_night_change(self):
        """
        将游戏阶段推进一步，在白天和黑夜之间切换。

        该函数会增加游戏阶段计数，确定当前的天数和时间（白天或黑夜），
        并向所有玩家广播当前的游戏阶段。如果是第一天之后的早晨，
        它会检查是否有玩家在夜间被标记为死亡。如果有，则广播被杀死的玩家列表
        并更新他们的状态。如果没有玩家被标记为死亡，
        则宣布夜间没有发生死亡事件。

        参数：
            无

        返回：
            无
        """

        self.stage += 1
        days, morning_dusk = self.get_game_stage()
        # self.broadcast(f"现在是第{days}天{'白天' if morning_dusk else '晚上'}")
        self.guard_tonight = []
        if morning_dusk == 1 and days > 1:
            if self.kill_tonight:
                self.kill_tonight = list(set(self.kill_tonight))
                self.broadcast(f"昨晚{str(self.kill_tonight)[1:-1]}号玩家被杀了")
                self.out(self.kill_tonight)
                self.kill_tonight = []
            else:
                self.broadcast(f"昨晚是个平安夜，没有人被杀")

    def get_game_stage(self):
        """
        以包含两个整数的元组形式返回当前游戏阶段。

        元组的第一个元素是当前天数（从1开始索引），
        第二个元素如果是白天则为1，如果是夜晚则为0。

        游戏阶段从0开始，每次调用 [day_night_change](file://e:\AIs\LLMsWerewolves\core\game.py#L483-L505) 方法时递增1。
        当前天数是游戏阶段整除2后加1的结果。
        当前时间（白天或夜晚）由游戏阶段除以2的余数决定。

        参数：
            无

        返回:
            tuple: 包含两个整数的元组 (days, morning_dusk)，
                其中 days 是当前天数（从1开始索引），
                morning_dusk 如果是白天则为1，如果是夜晚则为0。
        """
        days = self.stage // 2 + 1
        morning_dusk = (self.stage + 1) % 2  # 1表示白天，0表示晚上
        return days, morning_dusk

    def get_day(self):
        return self.get_game_stage()[0]

    def get_time(self):
        return TIMEDIC[self.get_game_stage()[1]]

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return f"第{self.get_day()}天{self.get_time()}"

    def __eq__(self, value):
        return self.id == value.id

    def set_logger(self):
        """
        设置日志记录器

        该函数负责创建日志目录、配置日志基本信息、创建日志记录器实例，
        并将日志记录器保存到实例变量中。

        参数:
            self: 类实例本身

        返回值:
            无返回值

        功能说明:
            1. 检查并创建日志目录
            2. 配置日志基本设置，包括日志级别、格式、输出文件等
            3. 创建指定ID的日志记录器
            4. 输出一条测试性的调试日志
            5. 将日志记录器保存到实例变量中供后续使用
        """

        # 创建文件处理器 (File Handler)
        if not os.path.exists("./log"):
            os.mkdir("./log")

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename=f"./log/{self.game_name}-id={self.id}.md",
            encoding="UTF-8",
        )

        logger = logging.getLogger(str(self.id))

        logger.debug("这是一条调试信息")

        self.logger = logger
