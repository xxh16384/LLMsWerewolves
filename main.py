from core.tools import find_max_key
from core.game import Game
from core.general import *



if __name__ == "__main__":
    # 输入路径配置
    # 控制台运行程序
    
    instructions_path = "./config/instructions.json"
    apis_path = "./config/api_template.json"
    players_info_path = "./config/player_info.json"
    game_name = input("请输入游戏窗口名称：")
    mode = input("请输入游戏模式（1、全自动模式(wip)，2、手动模式）：")

    game = Game(game_name, players_info_path, apis_path, instructions_path)

    if mode == "2":
        
        while True:
            print("\n ————————————————————\
                   \n 游戏开始! 请按顺序输入命令控制游戏进程:\
                   \n 1: 进入下一夜\
                   \n 2: 狼人杀人阶段\
                   \n 3: 预言家查验阶段\
                   \n 4: 女巫操作阶段\
                   \n 5: 公共讨论阶段\
                   \n 6: 投票阶段\
                   \n 7: 查看当前游戏状态\
                   \n 8: 结束游戏\
                   \n ————————————————————\n")
            print(f"【当前时间：{game}】\n")
            cmd = input("请输入命令(1-8): ")
            
            match(cmd):
                case "1":
                    # 进入下一夜
                    game.day_night_change()
                case "2":
                    # 狼人杀人
                    game.werewolf_killing()
                    print("狼人杀人阶段结束")
                case "3":
                    # 预言家查验
                    game.seer_seeing()
                    print("预言家查验阶段结束") 
                case "4":
                    # 女巫操作
                    game.witch_operation()
                    print("女巫操作阶段结束")
                case "5":
                    game.day_night_change()
                    print(f"已进入: 第{game.get_game_stage()[0]}天{TIMEDIC[game.get_game_stage()[1]]}")
                    # 公共讨论
                    game.public_discussion()
                    print("公共讨论阶段结束")
                case "6":
                    # 投票
                    result = find_max_key(game.vote())
                    game.out([result])
                    print("投票阶段结束")
                case "7":
                    # 显示当前状态
                    print(f"\n ————————————————————\
                            \n 当前游戏状态:\
                            \n 游戏名称: {game.game_name}\
                            \n 游戏阶段: 第{game.get_game_stage()[0]}天{TIMEDIC[game.get_game_stage()[1]]}\
                            \n 存活玩家:")
                    for player in game.get_players(alive=True):
                        print(f" {player}")
                case "8":
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