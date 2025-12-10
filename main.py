from core.tools import find_max_key
from core.game import Game
from core.general import *
from core.init import api_template_check, api_players_check, roles_divided


if __name__ == "__main__":
    # 输入路径配置
    # 控制台运行程序

    instructions_path = "./config/instructions.json"
    apis_path = "./config/api_template.json"  # 只存储api
    api_players_path = "./config/api_players.json"  # 只存储每个玩家的api，职业随机分配
    game_name = input("请输入游戏窗口名称：")
    mode = input("请输入游戏模式（1、全自动模式(wip)，2、手动模式）：")

    api_template_check(apis_path)
    api_players_check(apis_path, api_players_path)

    roles = roles_divided(api_players_path)

    game = Game(game_name, api_players_path, apis_path, instructions_path, roles)

    if mode == "2":

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
                    # 进入下一夜
                    game.day_night_change()
                case "2":
                    # 守护保人
                    game.guard_guarding()
                    print("守卫保卫阶段结束")
                case "3":
                    # 狼人杀人
                    game.werewolf_killing()
                    print("狼人杀人阶段结束")
                case "4":
                    # 预言家查验
                    game.seer_seeing()
                    print("预言家查验阶段结束")
                case "5":
                    # 女巫操作
                    game.witch_operation()
                    print("女巫操作阶段结束")
                case "6":
                    game.day_night_change()
                    print(f"已进入: {game}")
                    # 公共讨论
                    game.public_discussion()
                    print("公共讨论阶段结束")
                case "7":
                    # 投票
                    result = find_max_key(game.vote())
                    game.out([result])
                    print("投票阶段结束")
                case "8":
                    # 显示当前状态
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
                    # 结束游戏
                    print("游戏已手动结束")
                    exit(0)
                case _:
                    print("无效的命令,请重新输入")

            # 检查游戏是否结束
            if game.game_over():
                game.get_winner()
                break

    else:
        print("无效的命令，进程自动退出...")
