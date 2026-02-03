"""狼人杀游戏手动模式命令行启动脚本。

该脚本作为游戏的主要入口点，用于在控制台环境中以手动模式运行一局狼人杀游戏。
它首先会引导用户输入游戏的基本配置，如窗口名称和游戏模式。在选择了手动
模式后，脚本会初始化游戏环境，包括加载指令、API配置和玩家信息，并创建
一个核心的 `Game` 对象。

随后，脚本进入一个无限循环，通过命令行菜单接收用户输入。用户可以根据提示
输入数字指令来手动控制游戏的进程，例如：
- 推进游戏到下一个夜晚。
- 执行特定角色的夜间行动（守卫、狼人、预言家、女巫）。
- 开启白天的公共讨论和投票环节。
- 查看当前的游戏状态，包括存活玩家等信息。

每执行一个命令，脚本都会调用 `Game` 对象中相应的方法来更新游戏状态。在每
个循环的末尾，它会检查游戏是否满足结束条件。如果游戏结束，脚本会宣布
胜利方并终止程序。用户也可以随时输入 `-1` 来手动结束游戏。
"""

from core import *
from time import sleep
import os


if __name__ == "__main__":
    try:
        os.makedirs("config")
    except:
        pass

    instructions_path = "./config/instructions.json"
    apis_path = "./config/api_template.json"
    api_players_path = "./config/api_players.json"
    doc_path = "./doc/"
    game_name = cur_io.IO_input("请输入游戏窗口名称：")

    api_template_check(apis_path)
    api_players_check(apis_path, api_players_path)

    roles = roles_divided(api_players_path)

    role_json_made(roles, doc_path, instructions_path)

    game = Game(game_name, api_players_path, apis_path, instructions_path, roles)

    circle = 0
    game_end = False
    while True:
        circle += 1
        cur_io.IO_output(
            f"—————————————————————————————————————————————— 第{circle:^3d}轮 ———————————————————————————————————————————————"
        )
        cur_io.IO_output("当前存活玩家：")
        for player in game.get_players(alive=True):
            cur_io.IO_output(f" {player}")
        routines = iter(game.routines)
        for routine in routines:
            cur_routine = routine
            line_num = 100 - len(cur_routine[1]) * 2
            left_line_num = line_num // 2
            right_line_num = line_num - left_line_num
            cur_io.IO_output(
                f"{"—"*left_line_num} {cur_routine[1]} {"—"*right_line_num}"
            )
            cur_routine[0]()
            sleep(1)
            if game.gg or game.get_winner():
                game_end = True
        if game_end:
            break
