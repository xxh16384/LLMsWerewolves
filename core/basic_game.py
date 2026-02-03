# core/basic_game.py


import logging
import os
from random import choice
from openai import OpenAI
from .tools import (
    find_max_key,
    makeDic,
    read_reply,
)
from .context import Context
from .player import Player
from .io import cur_io
from .general import *


class BasicGame:
    def init_client(self):
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

        for player in self.players:
            player.init_system_prompt()

        Context(self, 0, self.role_prompts, self.get_players(t="id", alive=False))

        for routine in self.init_routines:
            if routine[1]:
                line_num = 100 - len(routine[0][1]) * 2
                left_line_num = line_num // 2
                right_line_num = line_num - left_line_num
                cur_io.IO_output(
                    f"{"—"*left_line_num} {routine[0][1]} {"—"*right_line_num}"
                )
                routine[0][0]()

    def init_role_prompts(self):
        """初始化要发送给所有玩家的角色提示词。

        此函数负责：
        1. 获取所有角色，整理成一个字符串。
        2. 这个字符串将被存储在一个类变量中，以待之后使用。
        """
        counts = sum([num for num in self.roles.values()])
        role_prompts = f"这是一局有{counts}个玩家的狼人杀游戏，一共有"
        for role in self.roles.keys():
            if self.roles[role] > 0:
                added_prompts = f"{str(self.roles[role])}个{PLAYERDIC[role]}，"
                role_prompts += added_prompts
        self.role_prompts = role_prompts

    def day_night_change(self):
        """处理昼夜交替，推进游戏阶段。

        此方法会增加游戏阶段计数器，并根据阶段判断是白天还是黑夜。
        在第二天及以后的早晨，它会公布前一晚的死讯，更新玩家状态，
        并重置当晚的守护和死亡列表。
        """
        self.stage += 1
        days, morning_dusk = self.get_game_stage()
        try:
            if self.guard_tonight:
                self.last_guard = self.guard_tonight[0]
                self.guard_tonight = []
            else:
                self.last_guard = 0
        except:
            pass
        if morning_dusk == 1 and days > 1:
            if self.kill_tonight or self.poisoned_tonight:
                try:
                    self.died_tonight = list(
                        set(self.kill_tonight + self.poisoned_tonight)
                    )
                except:
                    self.died_tonight = list(set(self.kill_tonight))

                self.broadcast(f"在{self}的前一晚，{self.died_tonight}号玩家被杀了")

                for died_player_id in self.died_tonight:
                    died_player = self.get_players_by_ids([died_player_id])[0]
                    if died_player.role == "poet":
                        self.broadcast(
                            f"{died_player.id}号玩家是吟游诗人！在他死之后，现在所有的好人都知道了这条消息。注意，狼人或者中立职业不会得知这条消息。",
                            faction="good",
                        )

                self.out(self.kill_tonight, "killed")
                self.kill_tonight = []
                try:
                    self.out(self.poisoned_tonight, "poisoned")
                    self.poisoned_tonight = []
                except:
                    pass
            else:
                self.broadcast(f"{self}的前一晚是个平安夜，没有人被杀")

    def public_discussion(self):
        """执行白天的公共讨论阶段。

        此函数向所有存活的玩家广播消息，提示他们进入公开讨论环节，
        并可以开始依次发言。
        """
        players_pending = self.get_players()
        for player in players_pending:
            player.pub_chat(0, "请公开讨论，在此阶段你可以简短发言，解释讨论理由。")

    def vote_police_section(self):
        """执行白天的警徽投票阶段，并统计投票结果，若有人得票最多且没有平票，即为警长。

        此函数通过vote函数和police函数，统计投票结果，并投出警长。
        """
        result = find_max_key(self.vote(t="police"))
        self.police_get(player_ids=[result])

    def vote_section(self):
        """执行白天的投票阶段，并统计投票结果，并将出局者投出。

        此函数通过vote函数和out函数，统计投票结果，并投出出局者。
        """
        result = find_max_key(self.vote(t="out"))
        self.out(player_ids=[result])

    def police_get(self, player_ids: list):
        """通过投票结果，决定今天的警长。

        此函数通过导入的投票结果，判断是否出现警长，并且标记其为警长。

        Args:
            player_ids (list): 需要成为警长的玩家ID列表。
        """
        if not player_ids:
            self.broadcast(f"在{self}的警徽阶段，出现了平票现象，没有任何人成为警长。")
            return
        players_pending = self.get_players_by_ids(player_ids)
        if not players_pending:
            self.broadcast(f"在{self}的警徽阶段，出现了平票现象，没有任何人成为警长。")
            return
        policeman = players_pending[0].id
        self.police = policeman
        self.broadcast(
            f"在{self}的警徽阶段，{self.police}号成为了警长。他在这一天的投票阶段持有两张票。"
        )

    def vote(self, t: str) -> dict:
        """执行白天的投票阶段，并统计投票结果。

        此函数向所有存活的玩家广播投票指示，收集每个玩家的投票选择。
        然后统计所有投票，确定每个被投票玩家的得票数。

        Args:
            type (str): 投票的目的，警徽投票或者出局投票。

        Returns:
            dict: 一个字典，键为被投票的玩家ID，值为该玩家获得的票数。
        """
        players_pending = self.get_players()
        for player in players_pending:
            if t == "out":
                player.pub_chat(
                    0,
                    "现在要将一个玩家投票出局。请投票，投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以简短发言，解释投票理由。",
                )
            elif t == "police":
                player.pub_chat(
                    0,
                    "现在要投票决出一个警长。请投票，投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以简短发言，解释投票理由。",
                )
        result = makeDic(players_pending)
        for player in players_pending:
            voted = read_reply(player)
            if voted:
                voted = int(voted[-1])
                if voted in self.get_players("id"):
                    try:
                        if not (
                            voted in self.voted_fools or player.id in self.voted_fools
                        ):
                            if t == "out" and player.id == self.police:
                                result[voted] += 2
                            else:
                                result[voted] += 1
                    except:
                        if t == "out" and player.id == self.police:
                            result[voted] += 2
                        else:
                            result[voted] += 1
        return result

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

    def get_players_by_factions(
        self, t: str = "object", alive: bool = True, faction: str = "bad"
    ) -> list:
        """根据玩家阵营获取对应的玩家ID或对象列表。

        Args:
            t (str, optional): 返回列表的元素类型。'object' 表示返回玩家对象，
                'id' 表示返回玩家ID。默认为 'object'。
            alive (bool, optional): 是否读取仅存活的玩家。
            faction (str, optional): 玩家的阵营。

        Returns:
            list: 包含与阵营匹配的Player的ID或对象的列表。
        """
        if t == "object":
            if alive:
                players_pending = [
                    player
                    for player in self.players
                    if LEGAL_ROLE[player.role] == faction and player.alive
                ]
            else:
                players_pending = [
                    player
                    for player in self.players
                    if LEGAL_ROLE[player.role] == faction
                ]
        elif t == "id":
            if alive:
                players_pending = [
                    player.id
                    for player in self.players
                    if LEGAL_ROLE[player.role] == faction and player.alive
                ]
            else:
                players_pending = [
                    player.id
                    for player in self.players
                    if LEGAL_ROLE[player.role] == faction
                ]
        return players_pending

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

    def broadcast(self, content: str, alive: bool = True, faction: str = "all"):
        """向游戏中的所有玩家广播一条消息。

        该消息将被添加到每个玩家的上下文中。

        Args:
            content (str): 要广播的消息内容。
            alive (bool, optional): 广播对象是否必须活着
            faction (str, optional): 要广播的对象。
        """
        if faction == "all":
            Context(self, 0, content, self.get_players(t="id", alive=alive))
        else:
            Context(
                self,
                0,
                content,
                self.get_players_by_factions(t="id", alive=alive, faction=faction),
            )

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

    # Deprecated
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
