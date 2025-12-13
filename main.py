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

from core.tools import find_max_key
from core.game import Game
from core.general import *
from core.init import api_template_check, api_players_check, roles_divided
from time import sleep


if __name__ == "__main__":
    instructions_path = "./config/instructions.json"
    apis_path = "./config/api_template.json"
    api_players_path = "./config/api_players.json"
    game_name = input("请输入游戏窗口名称：")
    mode = input("请输入游戏模式（1、全自动模式，2、手动模式，3、新·全自动模式）：")

    api_template_check(apis_path)
    api_players_check(apis_path, api_players_path)

    roles = roles_divided(api_players_path)

    game = Game(game_name, api_players_path, apis_path, instructions_path, roles)

    if mode == "1":
        while True:
            print(f"【当前阶段：{game}】\n")
            game.day_night_change()
            print("——————————守卫保卫阶段开始——————————")
            game.guard_guarding()
            sleep(1)
            print("——————————守卫保卫阶段结束——————————")
            print("——————————狼人杀人阶段开始——————————")
            game.werewolf_killing()
            sleep(1)
            print("——————————狼人杀人阶段结束——————————")
            print("——————————预言家查验阶段开始——————————")
            game.seer_seeing()
            sleep(1)
            print("——————————预言家查验阶段结束——————————")
            print("——————————女巫操作阶段开始——————————")
            game.witch_operation()
            sleep(1)
            print("——————————女巫操作阶段结束——————————")
            game.day_night_change()
            sleep(1)
            print(f"——————————已进入: {game}——————————")
            print("——————————公共讨论阶段开始——————————")
            game.public_discussion()
            sleep(1)
            print("——————————公共讨论阶段结束——————————")
            print("——————————投票阶段开始——————————")
            result = find_max_key(game.vote())
            game.out([result])
            sleep(1)
            print("——————————投票阶段结束——————————")
            print(
                f"\n ————————————————————————————————————————\
                    \n 当前游戏状态:\
                    \n 游戏名称: {game.game_name}\
                    \n 游戏阶段: {game}\
                    \n 存活玩家:"
            )
            for player in game.get_players(alive=True):
                print(f" {player}")
            input("请输入任意键以进入下一天：")

    elif mode == "3":
        circle = 0
        while True:
            circle += 1
            print(f"————————————————————第{circle}轮————————————————————")
            routines = iter(game.routines)
            for routine in routines:
                cur_routine = routine
                line_num = 10 - len(cur_routine[1])
                left_line_num = line_num // 2
                right_line_num = line_num - left_line_num
                print(f"{"—"*left_line_num} {cur_routine[1]} {"—"*right_line_num}")
                cur_routine[0]()
                sleep(1)

    elif mode == "2":

        while True:
            print(
                "\n ————————————————————\
                 \n 游戏开始! 请按顺序输入命令控制游戏进程:\
                 \n  1: 进入下一夜\
                 \n  2: 守护保人阶段\
                 \n  3: 狼人杀人阶段\
                 \n  4: 预言家查验阶段\
                 \n  5: 女巫操作阶段\
                 \n  6: 公共讨论阶段\
                 \n  7: 投票阶段\
                 \n  8: 查看当前游戏状态\
                 \n -1: 结束游戏\
                 \n ————————————————————\n"
            )
            print(f"【当前阶段：{game}】\n")
            cmd = input("请输入命令: ")

            match (cmd):
                case "1":
                    game.day_night_change()
                case "2":
                    game.guard_guarding()
                    print("——————————守卫保卫阶段结束——————————")
                case "3":
                    game.werewolf_killing()
                    print("——————————狼人杀人阶段结束——————————")
                case "4":
                    game.seer_seeing()
                    print("——————————预言家查验阶段结束——————————")
                case "5":
                    game.witch_operation()
                    print("——————————女巫操作阶段结束——————————")
                case "6":
                    game.day_night_change()
                    print(f"——————————已进入: {game}——————————")
                    game.public_discussion()
                    print("——————————公共讨论阶段结束——————————")
                case "7":
                    result = find_max_key(game.vote())
                    game.out([result])
                    print("——————————投票阶段结束——————————")
                case "8":
                    print(
                        f"\n ————————————————————\
                          \n 当前游戏状态:\
                          \n 游戏名称: {game.game_name}\
                          \n 游戏阶段: {game}\
                          \n 存活玩家:"
                    )
                    for player in game.get_players(alive=True):
                        print(f" {player}")
                case "-1":
                    print("游戏已手动结束")
                    exit(0)
                case _:
                    print("无效的命令,请重新输入")

            if game.game_over():
                game.get_winner()
                break

    else:
        print("无效的命令，进程自动退出...")
