from core import Player

class WebPlayer(Player):
    def __init__(self, role: str, id: int, using_preset: str, game):
        super().__init__(role, id, using_preset, game)