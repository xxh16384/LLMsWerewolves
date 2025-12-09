from core.tools import find_max_key
from core.game import Game

if __name__ == "__main__":
    # 输入路径配置
    # 控制台运行程序
    instructions_path = "./config/instructions.json"
    apis_path = "./config/api_template.json"
    players_info_path = "./config/player_info.json"
    game_name = input("请输入游戏名称：")
    mode = input("请输入游戏模式（1、全自动模式，2、手动模式）：")

    game = Game(game_name, players_info_path, apis_path, instructions_path)
    
    if mode == "2":
        # 增加手动控制游戏逻辑
        # 手动控制游戏进程
        
        while True:
            print("\n————————————————————")
            print("游戏开始! 输入命令控制游戏进程:")
            print("1: 进入下一夜")
            print("2: 狼人杀人阶段") 
            print("3: 预言家查验阶段")
            print("4: 女巫操作阶段")
            print("5: 公共讨论阶段")
            print("6: 投票阶段")
            print("7: 查看当前游戏状态")
            print("8: 结束游戏")
            print("————————————————————")
            cmd = input("\n请输入命令(1-8): ")
            
            if cmd == "1":
                # 进入下一夜
                game.day_night_change()
                print(f"已进入: 第{game.get_game_stage()[0]}天{'白天' if game.get_game_stage()[1] else '晚上'}")
            elif cmd == "2":
                # 狼人杀人
                game.werewolf_killing()
                print("狼人杀人阶段结束")
            elif cmd == "3":
                # 预言家查验
                game.seer_seeing()
                print("预言家查验阶段结束") 
            elif cmd == "4":
                # 女巫操作
                game.witch_operation()
                print("女巫操作阶段结束")
            elif cmd == "5":
                game.day_night_change()
                print(f"已进入: 第{game.get_game_stage()[0]}天{'白天' if game.get_game_stage()[1] else '晚上'}")
                # 公共讨论
                game.public_discussion()
                print("公共讨论阶段结束")
            elif cmd == "6":
                # 投票
                result = find_max_key(game.vote())
                game.out([result])
                print("投票阶段结束")
            elif cmd == "7":
                # 显示当前状态
                print(f"\n当前游戏状态:")
                print(f"游戏名称: {game.game_name}")
                print(f"游戏阶段: 第{game.get_game_stage()[0]}天{'白天' if game.get_game_stage()[1] else '晚上'}")
                print("\n存活玩家:")
                for player in game.get_players(alive=True):
                    print(f"玩家{player.id}({player.role})")
            elif cmd == "8":
                # 结束游戏
                print("游戏已手动结束")
                exit(0)
            else:
                print("无效的命令,请重新输入")
                
            # 检查游戏是否结束
            if game.game_over():
                game.get_winner()
                break
    elif mode == "1":
        # 全自动模式
        print("\n游戏开始! 自动控制游戏进程:")
        while not game.game_over():
            game.day_night_change()
            game.werewolf_killing()
            game.seer_seeing()
            game.witch_operation()
            game.day_night_change()
            if game.game_over():
                game.get_winner()
                break
            game.public_discussion()
            result = find_max_key(game.vote())
            game.out([result])
    else:
        print("无效的命令，进程自动退出...")