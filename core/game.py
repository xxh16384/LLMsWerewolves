from time import time
from .tools import (
    read_json,
    find_max_key,
    makeDic,
    read_reply,
)
from .context import Context
from .player import Player
from .basic_game import BasicGame
from .general import *


class Game(BasicGame):
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

        # 初始化角色提示词
        self.roles = roles.copy()
        self.init_role_prompts()

        # 初始化某些角色所需使用的列表
        self.init_special_role_prepartion()

        # 初始化游戏状态
        self.gg = False
        self.police = -1
        self.routine()

        # 初始化游戏上下文，玩家以及其使用的API
        self.clients = {}
        self.players = []
        self.init_client()

    def init_special_role_prepartion(self):
        """初始化特殊变量

        此函数负责初始化某些特殊角色所需要的变量，如女巫需要记录当晚毒的人。
        """
        self.kill_tonight = []
        if self.roles["witch"] > 0:
            self.poisoned_tonight = []
        if self.roles["guard"] > 0:
            self.guard_tonight = []
            self.last_guard = 0
        if self.roles["fool"] > 0:
            self.voted_fools = []

    def routine(self):
        def check(role):
            return self.roles[role] > 0

        routines = (
            ((self.day_night_change, "月亮升起"), True),
            ((self.guard_guarding, "守卫醒来"), check("guard")),
            ((self.werewolf_killing, "狼人醒来"), check("werewolf")),
            ((self.whitewolf_killing, "白狼醒来"), check("whitewolf")),
            ((self.seer_seeing, "预言家醒来"), check("seer")),
            ((self.witch_operation, "女巫醒来"), check("witch")),
            ((self.day_night_change, "太阳升起"), True),
            ((self.public_discussion, "公共讨论"), True),
            ((self.vote_police_section, "警长投票"), True),
            ((self.vote_section, "陶片逐人"), True),
        )

        self.routines = []
        for routine in routines:
            if routine[1]:
                self.routines.append(routine[0])

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

        if self.get_day() == 1:
            return

        guard = self.get_players(role="guard")
        if not guard:
            return
        guard = guard[0]

        talk_guard(
            f"你今晚要保护谁？要保护的玩家编号请用[]包围，若不保护人则输出[0]。注意，你不可连续两晚保护同一个人{"" if self.last_guard == 0 else "，你昨晚保护了["+str(self.last_guard)+"]号玩家，因此你今晚无法保护这个玩家"}。例如'我要保护[7]号玩家'或'我不想保护人，[0]'。可以简短的给出理由。"
        )
        target = read_reply(guard)
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
            Context(
                self, 0, message, self.get_players_by_factions(t="id", faction="bad")
            )

        # wolves = self.get_players(role="werewolf")

        wolves = self.get_players_by_factions(faction="bad")

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
            ToKilled = read_reply(wolf)
            if ToKilled and int(ToKilled[-1]) in self.get_players("id"):
                result[int(ToKilled[-1])] += 1

        killed = find_max_key(result)
        if killed and killed != 0:
            record_werewolf(f"在{self.get_day()}的晚上，{killed}号玩家被狼人标记要杀。")
            if not killed in self.guard_tonight:
                self.kill_tonight.append(killed)
        else:
            record_werewolf(f"在{self.get_day()}的晚上，狼人没有选择任何人要杀。")

    def whitewolf_killing(self):
        """处理白狼的夜晚杀人行动。

        此函数记录白狼的思考和投票，以决定当晚要击杀的玩家。
        它会收集白狼的投票，并将其记录到当晚的死亡候选列表中。
        如果目标未被守卫守护，则会最终被标记为死亡。
        """

        def talk_whitewolf(message: str):
            whitewolf.private_chat(0, message)

        def record_whitewolf(message: str):
            Context(self, 0, message, self.get_players(t="id", role="whitewolf"))

        if self.get_day() % 2 == 1:
            return

        whitewolf = self.get_players(role="whitewolf")
        if not whitewolf:
            return
        whitewolf = whitewolf[0]
        talk_whitewolf(
            "你是白狼，今晚你可以使用白狼之刃，杀死任一一名玩家，你可以为了削弱好人势力来杀死好人，也可以为了特殊胜利而杀死你的狼人队友。你今晚要杀谁？要查询的玩家编号请用[]包围，例如'我要杀死[7]号玩家'，你无论如何都必须要杀死一个人。可以简短的给出理由。"
        )
        target = read_reply(whitewolf)
        if target and target != 0:
            record_whitewolf(
                f"在{self.get_day()}的晚上，你使用白狼之刃，杀死了{target}号玩家。"
            )
        else:
            record_whitewolf(f"在{self.get_day()}的晚上，你没有杀死任何人。")

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
            "你今晚要查谁？要查询的玩家编号请用[]包围，例如'我要查询[7]号玩家'，你无论如何都必须要查询一个人。可以简短的给出理由。"
        )
        target = read_reply(seer)
        if target and target != 0:
            target_player = self.get_players_by_ids(target)[0]
            if target_player.role == "hiddenwolf":
                target_identity = "good"
            else:
                target_identity = LEGAL_ROLE[target_player.role]
            target_identity = TRANSLATE[target_identity]
            record_seer(
                f"在{self.get_day()}的晚上，你查的玩家是{target}号，他的身份是：{target_identity}，{"但注意，他也有可能是隐狼" if "hiddenwolf" in LEGAL_ROLE.keys() else ""}。"
            )
        else:
            record_seer(f"在{self.get_day()}的晚上，你没有查询任何人的身份。")

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
                cured = read_reply(witch)
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
            poisoned = read_reply(witch)
            if int(poisoned[-1]):
                witch.poison = True
                record_witch(
                    f"在{self.get_day()}的晚上，你选择了毒杀{int(poisoned[-1])}号玩家。"
                )
                self.poisoned_tonight.append(int(poisoned[-1]))
                witch.poison = False
        else:
            record_witch(f"在{self.get_day()}的晚上，你今晚没有毒，所以没有毒杀人。")

    def out(self, player_ids: list, ways: str = "voted"):
        """将一个或多个玩家标记为出局。

        此函数将指定ID列表中的玩家的存活状态设置为False，
        并向所有玩家广播出局信息。

        Args:
            player_ids (list): 需要出局的玩家ID列表。

        Raises:
            ValueError: 如果传入的玩家ID列表无效或找不到对应玩家。
        """
        if (not player_ids) and ways == "voted":
            self.broadcast(f"在{self}的投票阶段，由于出现了平票现象，所以出局失败。")
            return
        players_pending = self.get_players_by_ids(player_ids)
        if not players_pending:
            raise ValueError("出局失败")
        for outed_player in players_pending:
            outed_player.alive = False

            # 傻子检验
            try:
                if outed_player.fool and ways == "voted":
                    self.broadcast(
                        f"在{self}的投票阶段，{str(outed_player)}号玩家得到了最多票数……但他是傻子，并没有出局，之后他无法再投票，也无法被人投票。"
                    )
                    self.voted_fools.append(outed_player)
            except:
                if ways == "voted":
                    self.broadcast(
                        f"在{self}的投票阶段，{str(outed_player)}号玩家出局。"
                    )

            # 小丑检验
            try:
                if outed_player.joker and ways == "voted":
                    self.special_win(outed_player, "joker")
            except:
                pass

            # 猎人检验
            try:
                if outed_player.revenge and ways != "poisoned":
                    bcmessage = f"{outed_player.id}是猎人！他被{"投票出局" if ways == "voted" else "杀死"}了！他将在死前杀死一名任意玩家！"
                    pcmessage = "你要杀死谁？要杀死的玩家编号请用[]包围，例如'我要杀死[7]号玩家'。可以简短的给出理由，你必须要杀死一个人。"
                    self.broadcast(bcmessage)
                    outed_player.private_chat(0, pcmessage)
                    target = read_reply(outed_player)
                    self.broadcast(
                        f"{outed_player.id}号玩家作为猎人，在死后杀死了{target}号玩家！"
                    )
                    self.out(target, "killed")
            except:
                pass

            if self.gg:
                break

    def get_winner(self) -> str | None:
        """在游戏结束后，判断并宣布胜利方。

        该函数首先检查游戏是否结束。如果已结束，则根据场上存活的
        狼人与好人数量关系来确定胜者是“狼人”还是“好人”，并广播结果。

        Returns:
            str: 返回胜利阵营的名称 ("狼人" 或 "好人")。
        """
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
            print("【系统】游戏结束！狼人阵营获胜。")
            return "狼人"
        elif len(self.get_players(alive=True, role="werewolf")) == 0:
            Context(
                self,
                0,
                f"游戏结束，好人获胜",
                self.get_players(t="id", alive=False),
            )
            print("【系统】游戏结束！好人阵营获胜。")
            return "好人"
        return None

    def special_win(self, player_id: int, way: str) -> None:
        """管理特殊胜利的方式，比如说小丑被投票出局。

        该函数

        Returns:

        """
        match (way):
            case "joker":
                print("【系统】游戏结束！小丑单独获胜。")
                self.gg = True
