from core import Game,Context
from time import time
from web_player import WebPlayer
from openai import OpenAI

class WebGame(Game):
    def __init__(self, game_name, players_info, apis, instructions):

        # 这里players_info是一个字典，玩家编号为键，玩家信息为值预设和角色；instructions也是字典
        self.game_name = game_name
        self.stage = 0
        self.id = time()

        self.players_info = players_info.copy()
        self.apis = apis.copy()
        self.instructions = instructions.copy()

        self.clients = {}
        self.players = []

        role_counts = {}
        for player_id, player_data in players_info.items():
            role = player_data.get("role")
            if role:
                role_counts[role] = role_counts.get(role, 0) + 1
        self.roles = role_counts

        self.init_role_prompt()

        self.init_game()

        self.kill_tonight = []
        self.guard_tonight = []

    def give_role(self,key):
        return self.players_info[key]["role"]
    def init_game(self):
        for i in self.players_info.keys():
            if i == "0" or i == 0:
                continue
            role = self.give_role(i)
            preset = self.players_info[i]["preset"]
            if not preset in self.clients:
                client = OpenAI(
                    api_key=self.apis[preset]["api_key"],
                    base_url=self.apis[preset]["base_url"],
                )
                self.clients[preset] = client
            WebPlayer(role, int(i), preset, self)
        for i in self.players:
            i.init_system_prompt()
        Context(self, 0, self.role_prompts, self.get_players(t="id", alive=False))
