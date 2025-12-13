import logging
import os
from time import time
from random import choice
from .tools import read_json, extract_numbers_from_brackets, find_max_key, makeDic
from .context import Context
from .player import Player
from .general import *
from openai import OpenAI


class Game:
    def __init__(
        self,
        game_name: str,
        players_info_path: str,
        apis_path: str,
        instructions_path: str,
        roles: dict,
    ):
        """初始化一个狼人杀游戏实例。

        Args:
            game_name (str): 游戏名称。
            players_info_path (str): 包含玩家信息的JSON文件路径。
            apis_path (str): 包含API配置的JSON文件路径。
            instructions_path (str): 包含游戏指令的JSON文件路径。
            roles (dict): 一个包含角色及其数量的字典。
        """
        self.game_name = game_name
        self.stage = 0
        self.id = time()
        self.set_logger()

        self.instructions = read_json(instructions_path)
        self.apis = read_json(apis_path)
        self.players_info = read_json(players_info_path)

        self.clients = {}

        self.players = []

        self.roles = roles.copy()
        counts = sum([num for num in self.roles.values()])
        self.role_prompts = f"\
这是一局有{counts}个玩家的狼人杀游戏，一共有\
{str(self.roles["werewolf"]) + "个狼人，" if self.roles["werewolf"] > 0 else ""}\
{str(self.roles["villager"]) + "个村民，" if self.roles["villager"] > 0 else ""}\
{str(self.roles["seer"]) + "个预言家，" if self.roles["seer"] > 0 else ""}\
{str(self.roles["witch"]) + "个女巫，" if self.roles["witch"] > 0 else ""}\
{str(self.roles["guard"]) + "个守卫，" if self.roles["guard"] > 0 else ""}"

        self.init_game()

        self.routine()

        self.kill_tonight = []
        self.guard_tonight = []

    def routine(self):
        self.routines = [
            [self.day_night_change(), "月亮升起"],
            [self.guard_guarding(), "守卫醒来"],
            [self.werewolf_killing(), "狼人醒来"],
            [self.seer_seeing(), "预言家醒来"],
            [self.witch_operation(), "女巫醒来"],
            [self.day_night_change(), "太阳升起"],
            [self.public_discussion(), "公共讨论"],
            [self.vote_section(), "陶片逐人"],
        ]

    def day_night_change(self):
        """处理昼夜交替，推进游戏阶段。

        此方法会增加游戏阶段计数器，并根据阶段判断是白天还是黑夜。
        在第二天及以后的早晨，它会公布前一晚的死讯，更新玩家状态，
        并重置当晚的守护和死亡列表。
        """
        self.stage += 1
        days, morning_dusk = self.get_game_stage()
        self.guard_tonight = []
        if morning_dusk == 1 and days > 1:
            if self.kill_tonight:
                self.kill_tonight = list(set(self.kill_tonight))
                self.broadcast(f"昨晚{str(self.kill_tonight)[1:-1]}号玩家被杀了")
                self.out(self.kill_tonight)
                self.kill_tonight = []
            else:
                self.broadcast(f"昨晚是个平安夜，没有人被杀")

    def guard_guarding(self):
        """处理守卫的夜晚守护行动。

        该函数会与守卫玩家进行私聊，询问其当晚要守护的目标。
        获取目标后，将守护信息记录到守卫的上下文中，并更新当晚的守护列表。
        如果游戏中没有守卫角色，则直接返回。
        """

        def talk_guard(message: str):
            guard.private_chat(0, message)

        def record_guard(message: str):
            Context(self, 0, message, self.get_players(t="id", role="guard"))

        guard = self.get_players(role="guard")
        if not guard:
            return
        guard = guard[0]

        talk_guard(
            "你今晚要保护谁？要保护的玩家编号请用[]包围，若不保护人则输出[0]，例如'我要保护[7]号玩家'或'我不想保护人，[0]'。可以简短的给出理由。"
        )
        target = extract_numbers_from_brackets(guard.messages[-1]["content"])
        if target and target[0] != 0:
            record_guard(f"在{self.get_day()}的晚上，你保护了{target}号玩家。")
        self.guard_tonight.append(target[0])

    def werewolf_killing(self):
        """处理狼人团队的夜晚杀人行动。

        此函数协调狼人阵营的内部讨论和投票，以决定当晚要淘汰的玩家。
        它会收集所有狼人的投票，找出得票最多的目标，并将其记录到当晚的死亡候选列表中。
        如果目标未被守卫守护，则会最终被标记为死亡。
        """

        def talk_werewolf(target: Player, message: str):
            target.private_chat(0, message)

        def record_werewolf(message: str):
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
            record_werewolf(f"在{self.get_day()}的晚上，{killed}号玩家被狼人标记要杀。")
            if not killed in self.guard_tonight:
                self.kill_tonight.append(killed)
        else:
            record_werewolf(f"在{self.get_day()}的晚上，狼人没有选择任何人要杀。")

    def seer_seeing(self):
        """处理预言家的夜晚查验行动。

        该函数与预言家玩家进行私聊，询问其要查验身份的目标玩家。
        获取目标后，它会查询该玩家的真实身份，并将结果反馈给预言家。
        如果游戏中没有预言家角色，则直接返回。
        """

        def talk_seer(message: str):
            seer.private_chat(0, message)

        def record_seer(message: str):
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
            f"在{self.get_day()}的晚上，你查的玩家是{target}号，他的身份是{self.get_players_by_ids(target)[0].role}。"
        )

    def witch_operation(self):
        """处理女巫的夜晚操作，包括使用解药和毒药。

        此函数首先检查当晚是否有人被杀。如果有，且女巫拥有解药，
        会询问女巫是否救人。之后，如果女巫拥有毒药，会询问是否要毒杀一名玩家。
        根据女巫的决定更新游戏状态和玩家的生死。
        """

        def talk_witch(message: str):
            witch.private_chat(0, message)

        def record_witch(message: str):
            Context(self, 0, message, self.get_players(t="id", role="witch"))

        witch = self.get_players(role="witch")
        if not witch:
            return

        witch = witch[0]

        if self.kill_tonight:
            victim = self.kill_tonight[0]
            if witch.antidote:
                talk_witch(
                    f"在{self.get_day()}的晚上，{victim}号玩家被杀了，你可以选择救他或者不救，选择结果用[]包围，救请写[1]，不救请写[0]，你可以简短的给出理由。"
                )
                cured = extract_numbers_from_brackets(witch.messages[-1]["content"])
                if cured and int(cured[-1]):
                    witch.antidote = True
                    record_witch(
                        f"在{self.get_day()}的晚上，{victim}号玩家被杀了，你选择了救他。"
                    )
                    self.kill_tonight.pop(0)
                    witch.antidote = False
            else:
                record_witch(
                    f"在{self.get_day()}的晚上，{victim}号玩家被杀了，但你没有解药，没法救他。"
                )
        else:
            record_witch(f"在{self.get_day()}的晚上，在你的行动阶段之前，没有人死。")

        if witch.poison:
            talk_witch(
                f"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。",
            )
            poisoned = extract_numbers_from_brackets(witch.messages[-1]["content"])
            if int(poisoned[-1]):
                witch.poison = True
                record_witch(
                    f"在{self.get_day()}的晚上，你选择了毒杀{int(poisoned[-1])}号玩家。"
                )
                self.kill_tonight.append(int(poisoned[-1]))
                witch.poison = False
        else:
            record_witch(f"在{self.get_day()}的晚上，你今晚没有毒，所以没有毒杀人。")

    def public_discussion(self):
        """执行白天的公共讨论阶段。

        此函数向所有存活的玩家广播消息，提示他们进入公开讨论环节，
        并可以开始依次发言。
        """
        players_pending = self.get_players()
        for player in players_pending:
            player.pub_chat(0, "请公开讨论，在此阶段你可以简短发言，解释讨论理由。")

    def vote_section(self):
        """执行白天的投票阶段，并统计投票结果，并将出局者投出。

        此函数通过vote函数和out函数，统计投票结果，并投出出局者。
        """
        result = find_max_key(self.vote())
        self.out([result])

    def vote(self) -> dict:
        """执行白天的投票阶段，并统计投票结果。

        此函数向所有存活的玩家广播投票指示，收集每个玩家的投票选择。
        然后统计所有投票，确定每个被投票玩家的得票数。

        Returns:
            dict: 一个字典，键为被投票的玩家ID，值为该玩家获得的票数。
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

    def out(self, player_ids: list):
        """将一个或多个玩家标记为出局。

        此函数将指定ID列表中的玩家的存活状态设置为False，
        并向所有玩家广播出局信息。

        Args:
            player_ids (list): 需要出局的玩家ID列表。

        Raises:
            ValueError: 如果传入的玩家ID列表无效或找不到对应玩家。
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
        """将一个或多个出局的玩家重新标记为存活。

        此函数将指定ID列表中的玩家的存活状态设置为True，
        并向所有玩家广播该玩家回归游戏的信息。

        Args:
            player_ids (list): 需要恢复存活状态的玩家ID列表。

        Raises:
            ValueError: 如果传入的玩家ID列表无效或找不到对应玩家。
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

    def game_over(self) -> int:
        """检查游戏是否满足结束条件。

        游戏结束条件：
        1. 狼人数量大于或等于好人数量。
        2. 所有狼人均已出局。

        Returns:
            int: 如果游戏结束则返回1，否则返回0。
        """
        if (
            len(self.get_players(alive=True))
            - 2 * len(self.get_players(alive=True, role="werewolf"))
            < 0
        ):
            return 1
        elif len(self.get_players(alive=True, role="werewolf")) == 0:
            return 1
        else:
            return 0

    def get_winner(self) -> str:
        """在游戏结束后，判断并宣布胜利方。

        该函数首先检查游戏是否结束。如果已结束，则根据场上存活的
        狼人与好人数量关系来确定胜者是“狼人”还是“好人”，并广播结果。

        Returns:
            str: 返回胜利阵营的名称 ("狼人" 或 "好人")。
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

    def init_game(self):
        """初始化游戏的核心组件，包括玩家和上下文。

        此函数负责：
        1. 根据配置信息创建所有玩家对象并分配角色。
        2. 为每个玩家初始化API客户端。
        3. 为每个玩家初始化系统提示信息。
        4. 创建全局游戏上下文。
        """
        for i in self.players_info.keys():
            if i == "0" or i == 0:
                continue
            role = self.give_role()
            preset = self.players_info[i]["preset"]
            if not preset in self.clients:
                client = OpenAI(
                    api_key=self.apis[preset]["api_key"],
                    base_url=self.apis[preset]["base_url"],
                )
                self.clients[preset] = client
            Player(role, int(i), preset, self)
        for i in self.players:
            i.init_system_prompt()
        Context(self, 0, self.role_prompts, self.get_players(t="id", alive=False))

    def set_logger(self):
        """配置并初始化日志记录器。

        该函数会创建日志目录（如果不存在），并设置日志的基本配置，
        包括日志级别、格式和输出文件。日志文件名包含游戏名称和ID。
        """
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

    def get_players(
        self, t: str = "object", alive: bool = True, role: str = "all"
    ) -> list:
        """根据条件筛选并获取玩家列表。

        Args:
            t (str, optional): 返回列表的元素类型。'object' 表示返回玩家对象，
                'id' 表示返回玩家ID。默认为 'object'。
            alive (bool, optional): 是否只返回存活的玩家。True表示只返回存活玩家。
                默认为 True。
            role (str, optional): 筛选特定角色。'all' 表示不限角色。
                默认为 'all'。

        Returns:
            list: 符合筛选条件的玩家对象或ID的列表。
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

    def get_players_by_ids(self, ids: list) -> list:
        """根据玩家ID列表获取对应的玩家对象列表。

        Args:
            ids (list): 包含玩家ID的列表。

        Returns:
            list: 包含与ID匹配的Player对象的列表。
        """
        ids = [int(i) for i in ids]
        players_pending = [i for i in self.players if i.id in ids]
        return players_pending

    def broadcast(self, content: str):
        """向游戏中的所有玩家广播一条消息。

        该消息将被添加到每个玩家（无论存活与否）的上下文中。

        Args:
            content (str): 要广播的消息内容。
        """
        Context(self, 0, content, self.get_players(t="id", alive=False))

    def give_role(self) -> str:
        """从剩余的角色池中随机分配一个角色。

        此函数会从可用的角色列表中随机选择一个，然后将该角色的可用数量减一。
        如果某个角色的数量减到零，则从可分配列表中移除。

        Returns:
            str: 分配出的角色名称。
        """
        new_role = choice(list(self.roles.keys()))
        self.roles[new_role] -= 1
        if self.roles[new_role] == 0:
            del self.roles[new_role]
        return new_role

    def get_game_stage(self) -> tuple:
        """计算并返回当前的游戏天数和时间（白天/黑夜）。

        天数从1开始。白天用1表示，夜晚用0表示。

        Returns:
            tuple: 一个包含两个整数的元组 (天数, 时间标记)。
        """
        days = self.stage // 2 + 1
        morning_dusk = (self.stage + 1) % 2
        return days, morning_dusk

    def get_day(self) -> str:
        """获取当前游戏的天数。

        Returns:
            int: 当前的天数。
        """
        return self.get_game_stage()[0]

    def get_time(self) -> str:
        """获取当前游戏的时间（白天或晚上）。

        Returns:
            str: 表示当前时间的字符串（例如 "白天" 或 "晚上"）。
        """
        return TIMEDIC[self.get_game_stage()[1]]

    def __hash__(self) -> int:
        """返回游戏实例的哈希值，基于其唯一ID。"""
        return hash(self.id)

    def __str__(self) -> str:
        """返回描述当前游戏状态的字符串。"""
        return f"第{self.get_day()}天{self.get_time()}"

    def __eq__(self, value) -> bool:
        """判断两个游戏实例是否相等，基于它们的ID。"""
        return self.id == value.id
