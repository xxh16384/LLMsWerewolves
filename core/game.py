from openai import OpenAI
import json
import logging
import os
from time import time
from core.tools import read_json, extract_numbers_from_brackets, find_max_key
from .context import Context
from .player import Player
from core.general import *



class Game:
    def __init__(self, game_name, players_info_path, apis_path, instructions_path):
        """
        Initialize a new game instance.

        Args:
            game_name (str): the name of the game
            players_info_path (str): the path to the players info json file
            apis_path (str): the path to the apis json file
            instructions_path (str): the path to the instructions json file

        Attributes:
            game_name (str): the name of the game
            instructions (dict): the instructions for the game
            apis (dict): the apis for the game
            players_info (dict): the players info for the game
            players (list): the players in the game
            id (int): the id of the game
            stage (int): the current stage of the game
            kill_tonight (list): the players to be killed tonight
        """
        self.game_name = game_name
        self.stage = 0
        self.id = time()
        self.set_logger()
        
        self.instructions = read_json(instructions_path)
        self.apis = read_json(apis_path)
        self.players_info = read_json(players_info_path)
        
        self.client = OpenAI(api_key = self.apis["Model abbreviation"]["api_key"], base_url = self.apis["Model abbreviation"]["base_url"])
        
        self.players = []
        self.init_game()
        self.kill_tonight = []


    def set_logger(self):
        """
        Set up the logger for the game.

        The logger will output logs to the console and a markdown file
        named `<game_name>.md` in the `log` directory.

        Args:
            game_name (str): The name of the game.

        Returns:
            None
        """
        
        logger = logging.getLogger(str(self.id))
        logger.setLevel(logging.DEBUG)

        # 创建控制台处理器 (Console Handler)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # 创建文件处理器 (File Handler)
        if not os.path.exists("./log"):
            os.mkdir("./log")
        log_file_path = f"./log/{self.game_name}-id={self.id}.md"
        fh = logging.FileHandler(log_file_path, encoding="UTF-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(
            '**%(asctime)s - %(levelname)s**\n%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))

        # 设置日志格式
        formatter = logging.Formatter('**%(asctime)s - %(levelname)s**\n%(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        # 将处理器添加到 logger
        logger.addHandler(ch)
        logger.addHandler(fh)

        # 初始化日志文件内容
        with open(log_file_path, "w", encoding="UTF-8") as f:
            f.write(f"# {self.game_name}\n\n")

        self.logger = logger


    def init_game(self):
        """
        Initializes the game by creating player instances and setting up the initial context.

        This function iterates over the players_info dictionary to create Player
        objects for each player, excluding the entry with key "0". It then initializes
        system prompts for each player and sets up the initial game context with a
        broadcast message containing the game description.

        The initial game context is created with visibility to all players.

        """

        for i in self.players_info.keys():
            if i == "0" or i == 0:
                continue
            roles = self.players_info[i]["role"]
            Player(roles,int(i),self)
        for i in self.players:
            i.init_system_prompt()
        Context(self,0,self.players_info["0"],self.get_players(t="id",alive=False))


    def get_players(self,t = "object",alive = True , role = "all"):
        """
        Retrieves a list of players based on specified criteria.

        Args:
            t (str): Determines the return type. If "object", returns player objects.
                    If "id", returns player ids. Defaults to "object".
            alive (bool): If True, only includes players who are alive.
                        If False, includes all players regardless of status. Defaults to True.
            role (str): Specifies the role of players to retrieve. If "all", retrieves players of all roles.
                        Otherwise, retrieves players with the specified role. Defaults to "all".

        Returns:
            list: A list of players or player ids based on the criteria specified by the arguments.
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


    def get_players_by_ids(self,ids:list):
        """
        Returns a list of players according to given ids.

        Args:
            ids (list): A list of player ids.

        Returns:
            list: A list of players with the given ids.
        """
        ids = [int(i) for i in ids]
        players_pending = [i for i in self.players if i.id in ids]
        return players_pending


    def werewolf_killing(self):
        """
        Executes the werewolf killing phase during the night.

        This function handles the process where werewolf players decide which player
        to kill during the night. It sends a message to all werewolf players asking
        them to select a target for elimination. The players then vote on a target
        and the one with the most votes is marked for killing. If a player is
        successfully chosen to be killed, a context message is created to indicate
        the player's elimination. If no decision is reached, a failure message is
        logged.

        The function updates the `kill_tonight` list with the id of the player
        chosen to be killed.

        Returns:
            None
        """

        players_pending = self.get_players(role="werewolf")
        if not players_pending:
            return
        content = "今晚你想杀谁？"
        for i in players_pending:
            i.private_chat(0,content)
        content = "请进行杀人投票，杀人投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以自由发言解释杀人理由。"
        for i in players_pending:
            i.private_chat(0,content)
        result = {i.id:0 for i in self.get_players()}
        for i in players_pending:
            voted = extract_numbers_from_brackets(i.messages[-1]['content'])
            if voted and int(voted[-1]) in self.get_players("id"):
                result[int(voted[-1])] += 1
        killed = find_max_key(result)
        if killed:
            Context(self,0,f"今晚{killed}号玩家被杀了",self.get_players(t="id",role="werewolf",alive=False))
            self.kill_tonight.append(killed)
        else:
            Context(self,0,f"击杀失败",self.get_players(t="id",role="werewolf",alive=False))


    def seer_seeing(self):
        """
        Now it's the seer's turn to see someone's role.

        1. The seer is asked to input the id of the player they want to see.
        2. The seer is given the role of the player they want to see.

        The message flow is as follows:
        Server -> Seer: "你今晚要查谁？"
        Seer -> Server: "[7]号玩家"
        Server -> Seer: "你今晚要查的玩家是7号玩家，他的身份是witch"
        """
        seer = self.get_players(role="seer",alive=False)
        if not seer:
            return
        seer = seer[0]
        if not seer.alive:
            return
        seer.private_chat(0,"你今晚要查谁？要查询的玩家编号请用[]包围，例如'我要查询[7]号玩家'。可以简短的给出理由。")
        target = extract_numbers_from_brackets(seer.messages[-1]['content'])
        seer.private_chat(0,f"你今晚要查的玩家是{self.get_players_by_ids(target)[0]}，他的身份是{self.get_players_by_ids(target)[0].role}")


    def witch_operation(self):
        """
        女巫的操作
        如果今晚有人被杀，女巫可以选择救他或者不救
        如果女巫选择救他，女巫将被标记为抗毒
        如果女巫选择不救，女巫可以选择毒杀别人
        如果女巫选择毒杀，女巫将被标记为毒药
        如果女巫没有毒药，女巫不能毒杀
        """
        witch = self.get_players(role="witch",alive=False)
        if not witch:
            return
        witch = witch[0]
        if not witch.alive:
            return
        if self.kill_tonight:
            if not witch.poison and not witch.antidote:
                witch.private_chat(0,f"今晚{self.kill_tonight}号玩家被杀了，你可以选择救或者不救，选择结果用[]包围，例如要救{self.kill_tonight[0]}号玩家，请写[{self.kill_tonight[0]}]，不救请写[0]，你可以简短的给出理由。另外，你今晚还有毒药，如果不救，你可以选择毒杀别人，如果不救，是否毒杀将在下一条消息中选择，本次回复无需选择，只需要回答救或者不救这一问题。")
                voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                if voted and int(voted[-1]):
                    witch.antidote = True
                    Context(self,0,f"今晚{self.kill_tonight}号玩家被杀了，你选择了救{voted[-1]}号玩家",self.get_players(t="id",alive=False,role="witch"))
                    self.kill_tonight.remove(int(voted[-1]))
                else:
                    Context(self,0,f"今晚{self.kill_tonight}号玩家被杀了，你选择了不救他",self.get_players(t="id",alive=False,role="witch"))
                    witch.private_chat(0,f"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。")
                    voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                    if int(voted[-1]):
                        witch.poison = True
                        Context(self,0,f"今晚{self.kill_tonight}号玩家被杀了，你选择了毒杀{int(voted[-1])}号玩家",self.get_players(t="id",alive=False,role="witch"))
                        self.kill_tonight.append(int(voted[-1]))
                    else:
                        Context(self,0,f"今晚{self.kill_tonight}号玩家被杀了，你选择了不毒杀",self.get_players(t="id",alive=False,role="witch"))
            elif not witch.antidote and witch.poison:
                witch.private_chat(0,f"今晚{self.kill_tonight}号玩家被杀了，你可以选择救他或者不救，选择结果用[]包围，救请写[1]，不救请写[0]，你可以简短的给出理由。另外，你今晚没有毒药了。")
                voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                if voted and int(voted[-1]) == 1:
                    witch.antidote = True
                    Context(self,0,f"今晚{self.kill_tonight}号玩家被杀了，你选择了救他",self.get_players(t="id",alive=False,role="witch"))
                    self.kill_tonight.remove(int(voted[-1]))
            elif witch.antidote and not witch.poison:
                witch.private_chat(0,"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。")
                voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                if int(voted[-1]):
                    witch.poison = True
                    Context(self,0,f"你选择了毒杀{int(voted[-1])}号玩家",self.get_players(t="id",alive=False,role="witch"))
                    self.kill_tonight.append(int(voted[-1]))
                else:
                    Context(self,0,f"你选择了不毒杀",self.get_players(t="id",alive=False,role="witch"))
            else:
                pass
        else:
            if not witch.poison:
                witch.private_chat(0,"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。")
                voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                if int(voted[-1]):
                    witch.poison = True
                    Context(self,0,f"你选择了毒杀{int(voted[-1])}号玩家",self.get_players(t="id",alive=False,role="witch"))
                    self.get_players_by_ids([int(voted[-1])])[0].alive = False
                else:
                    Context(self,0,f"你选择了不毒杀",self.get_players(t="id",alive=False,role="witch"))
            else:
                pass


    def public_discussion(self):
        """
        Public discussion process. Sends a message to all players to discuss,
        then collects all the discussion content and shows it to all players.

        Returns:
            None
        """
        players_pending = self.get_players()
        content = "请公开讨论，在此阶段你可以简短发言，解释讨论理由。"
        Context(self,0,content,self.get_players(t="id",alive=False))
        for i in players_pending:
            i.pub_chat(0,content,add_to_context=False)


    def vote(self) -> dict:
        """
        Voting process. First, sends a message to all players to vote. Then,
        collects all the votes and returns a dictionary where the keys are the
        player ids and the values are the number of votes they got.

        Returns:
            dict: A dictionary where the keys are the player ids and the values
                are the number of votes they got.
        """
        players_pending = self.get_players()
        content = "请投票，投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以简短发言，解释投票理由。"
        Context(self,0,content,self.get_players(t="id",alive=False))
        for i in players_pending:
            i.pub_chat(0,content,add_to_context=False)
        result = {i.id:0 for i in players_pending}
        for i in players_pending:
            voted = extract_numbers_from_brackets(i.messages[-1]['content'])
            if voted and int(voted[-1]) in self.get_players("id"):
                            result[int(voted[-1])] += 1
        return result


    def game_over(self) -> int:
        """
        Determines if the game is over and declares the winner.

        Checks the number of alive players and compares the number of werewolves to the
        number of non-werewolf players. If the number of werewolves is greater than or
        equal to the non-werewolf players, the werewolves win. If there are no remaining
        werewolves, the non-werewolf players win. Returns 1 if the game is over, otherwise 0.

        Returns:
            int: 1 if the game is over (either werewolves or non-werewolves have won),
            0 if the game is not yet over.
        """

        if len(self.get_players(alive=True)) - 2*len(self.get_players(alive=True,role="werewolf")) < 0: # 好人数量小于狼人数量
            return 1
        elif len(self.get_players(alive=True,role="werewolf")) == 0:
            return 1
        else:
            return 0


    def get_winner(self) -> str:
        if self.game_over():
            if len(self.get_players(alive=True)) - 2*len(self.get_players(alive=True,role="werewolf")) < 0:
                Context(self,0,f"游戏结束，狼人获胜",self.get_players(t="id",alive=False))
                return "狼人"
            elif len(self.get_players(alive=True,role="werewolf")) == 0:
                Context(self,0,f"游戏结束，好人获胜",self.get_players(t="id",alive=False))
                return "好人"


    def private_chat(self,player_id:int,content:str):
        """
        Allows a player to send a private chat message to the game.

        Args:
            player_id (int): The ID of the player sending the message.
            content (str): The content of the chat message to be sent.
        """
        self.get_players_by_ids([player_id])[0].private_chat(0,content)


    def public_chat(self,player_id:int,content:str,add_to_context:bool=True):
        """
        Allows a player to send a public chat message.

        Args:
            player_id (int): The ID of the player sending the message.
            content (str): The content of the chat message to be sent.
        """

        self.get_players_by_ids([player_id])[0].pub_chat(0,content,add_to_context)


    def broadcast(self,content):
        """
        Broadcast a message to all players.

        Args:
            content (str): content of the message to be broadcasted
        """
        Context(self,0,content,self.get_players(t="id",alive=False))


    def out(self,player_ids:list):
        """
        to out players, given player_ids list.
        this will directly set the alive status of given players to False,
        and broadcast the message to all players.

        Args:
            player_ids (list): list of player ids
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


    def no_out(self,player_ids:list):
        """
        to no out players, given player_ids list.
        this will directly set the alive status of given players to True,
        and broadcast the message to all players.
        Args:
            player_ids (list): list of player ids
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


    def day_night_change(self):
        """
        Advances the game stage by one, transitioning between day and night.

        This function increments the game stage, determines the current day and time (day or night),
        and broadcasts the current game stage to all players. If it is morning of any day after the first,
        it checks if any players were marked to be killed overnight. If there are, it broadcasts the list
        of players who were killed and updates their status. If no players were marked for death,
        it announces that no deaths occurred overnight.
        """

        self.stage += 1
        days,morning_dusk = self.get_game_stage()
        self.broadcast(f"现在是第{days}天{'白天' if morning_dusk else '晚上'}")
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
        Returns the current game stage as a tuple of two integers.

        The first element of the tuple is the current day number (1-indexed),
        and the second element is 1 if the current time is day, and 0 if it
        is night.

        The game stage starts at 0, and increments by 1 each time the
        day_night_change method is called. The current day number is the
        integer division of the game stage by 2, plus 1. The current time
        (day or night) is determined by the remainder of the game stage
        divided by 2.

        Returns:
            tuple: A tuple of two integers, (days, morning_dusk),
                where days is the current day number (1-indexed), and
                morning_dusk is 1 if the current time is day, and 0 if
                it is night.
        """
        days = self.stage//2 + 1
        morning_dusk = (self.stage + 1) % 2 # 1表示白天，0表示晚上
        return days, morning_dusk


    def __hash__(self):
        return hash(self.id)


    def __str__(self):
        return f"第{self.get_game_stage()[0]}天{TIMEDIC[self.get_game_stage()[1]]}"


    def __eq__(self, value):
        return self.id == value.id