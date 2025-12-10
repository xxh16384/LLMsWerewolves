from core.tools import find_max_key
from core.game import Game
from core.general import *
import json
from dotenv import load_dotenv
import os
from core.tools import read_json, print_json


def api_template_check(apis_path):
    """
    判定是否有api_template.json，如果没有的话就辅助填充。
    """
    try:
        apis = read_json(apis_path)
        print(
            "\n ——————————————————\
             \n 检测到可用api预设，\
             \n 你可以忽略此条提示。"
        )
    except:
        print(
            "\n ————————————————————\
             \n 未检测到可用api预设，\
             \n 进入辅助填充阶段。\
             \n 理论上来讲你只会进入此页面一次。"
        )
        apis = {}
        api_id = 1
        api_preset = "无"
        api_url = "无"
        api_key = "无"
        api_model = "无"
        while True:
            print(
                f"\n ————————————————————\
                  \n 请填写{api_id}号api预设的信息，\
                  \n 当前正在记录的api预设信息：\
                  \n  1: 预设名：{api_preset}\
                  \n  2: 预设url：{api_url}\
                  \n  3: 预设密钥：{api_key}\
                  \n  4: 预设模型：{api_model}\
                  \n  9: 查看所有填写了的所有api预设\
                  \n  0: 完成这份api预设填写\
                  \n -1: 完成所有api预设信息填写"
            )
            choice = input("输入对应数字以更新信息：")
            match (choice):
                case "1":
                    while api_preset == -1:
                        api_preset = input(
                            f"{api_id}号预设名字(自定义，仅用于和player对应，不可为-1)："
                        )
                case "2":
                    api_url = input(
                        f"{api_id}号预设所使用api的url(请使用openai兼容格式)："
                    )
                case "3":
                    api_key = input(
                        f"{api_id}号预设所使用api的密钥(仅保存在本地，不会上传到云端)："
                    )
                case "4":
                    api_model = input(
                        f"{api_id}号预设所使用api的模型(输出完整名字，输入-1以查询当前api所有模型(WIP))："
                    )
                case "9":
                    print_json(apis)
                    choice2 = input(
                        "若有想要删除的api预设，在此输入那个预设的名字，否则输入-1。"
                    )
                    if choice2 != -1:
                        try:
                            del apis[choice2]
                        except:
                            print("想要删除的预设不存在，已经自动跳出")
                case "0":
                    each_api = {
                        "api_key": api_key,
                        "base_url": api_url,
                        "model_name": api_model,
                    }
                    apis[api_preset] = each_api.copy()
                    api_preset = "无"
                    api_url = "无"
                    api_key = "无"
                    api_model = "无"
                    api_id += 1
                case "-1":
                    try:
                        apis_json = json.dumps(apis, ensure_ascii=False, indent=4)
                        with open(apis_path, "w", encoding="utf-8") as f:
                            f.write(apis_json)
                        break
                    except:
                        print("写入json失败，我也不知道什么问题，自检吧")


def api_players_check(apis_path, api_players_path):
    """
    判定是否有api_players.json，如果没有的话就辅助填充。
    """
    apis = read_json(apis_path)
    try:
        players = read_json(api_players_path)
        print(
            "\n ——————————————————\
             \n 检测到可用Player预设，\
             \n 你可以忽略此条提示。"
        )
    except:
        print(
            "\n ————————————————————\
             \n 未检测到可用Player预设，\
             \n 进入辅助填充阶段。\
             \n 理论上来讲你只会进入此页面一次。"
        )
        player_id = 1
        player_preset = "无"
        while True:
            print(
                f"\n ————————————————————\
                  \n 请填写{player_id}号Player对应的预设的信息，\
                  \n 当前正在记录的Player预设信息：\
                  \n  1: 预设名：{player_preset}\
                  \n  8: 查看所有填写了的所有api预设\
                  \n  9: 查看所有填写了的所有Player预设\
                  \n  0: 完成这份Player预设填写\
                  \n -1: 完成所有Player预设信息填写"
            )
            choice = input("输入对应数字以更新信息：")
            match (choice):
                case "1":
                    player_preset = input(f"{player_id}号Player对应的预设名字：")
                case "8":
                    print_json(apis)
                case "9":
                    print_json(players)
                case "0":
                    each_player = {"preset": player_preset}
                    players[player_id] = each_player.copy()
                    player_preset = "无"
                    player_id += 1
                case "-1":
                    try:
                        player_json = json.dumps(players, ensure_ascii=False, indent=4)
                        with open(api_players_path, "w", encoding="utf-8") as f:
                            f.write(player_json)
                        break
                    except:
                        print("写入json失败，我也不知道什么问题，自检吧")
    return apis


def roles_divided(api_players_path):
    players = read_json(api_players_path)
    counts = len(players)
    roles = {}
    roles["werewolf"] = 3
    roles["seer"] = 1
    roles["witch"] = 1
    roles["guard"] = 1
    while True:
        roles["villager"] = (
            counts - roles["werewolf"] - roles["seer"] - roles["witch"] - roles["guard"]
        )
        bad_guy = roles["werewolf"]
        good_guy = roles["villager"] + roles["seer"] + roles["witch"] + roles["guard"]
        print(
            f"\n ——————————————————\
              \n 请输入这一局的职业划分，\
              \n [a/b]中，a代表加1人，b代表减1人\
              \n [1/11] 狼人 数量 : {roles["werewolf"]:2d}\
              \n [2/12]预言家数量 : {roles["seer"]:2d}\
              \n [3/13] 女巫 数量 : {roles["witch"]:2d}\
              \n [4/14] 守卫 数量 : {roles["guard"]:2d}\
              \n [----] 平民 数量 : {roles["villager"]:2d}\
              \n [0]    完成职业划分"
        )
        choice = input("请输入；")

        match (choice):
            case "1":
                if roles["villager"] > 0:
                    roles["werewolf"] += 1
                    roles["villager"] -= 1
                else:
                    print("平民数量不足，无法增加！")
            case "11":
                if roles["werewolf"] > 0:
                    roles["werewolf"] -= 1
                    roles["villgaer"] += 1
                else:
                    print("狼人数量不足，无法减少！")
            case "2":
                if roles["villager"] > 0:
                    roles["seer"] += 1
                    roles["villager"] -= 1
                elif roles["seer"] == 0:
                    print("平民数量不足，无法增加！")
                else:
                    print("预言家数量无法大于一个！")
            case "12":
                if roles["seer"] > 0:
                    roles["seer"] -= 1
                    roles["villgaer"] += 1
                else:
                    print("预言家数量不足，无法减少！")
            case "3":
                if roles["villager"] > 0:
                    roles["witch"] += 1
                    roles["villager"] -= 1
                elif roles["witch"] == 0:
                    print("平民数量不足，无法增加！")
                else:
                    print("女巫数量无法大于一个！")
            case "13":
                if roles["witch"] > 0:
                    roles["witch"] -= 1
                    roles["villgaer"] += 1
                else:
                    print("女巫数量不足，无法减少！")
            case "4":
                if roles["villager"] > 0:
                    roles["guard"] += 1
                    roles["villager"] -= 1
                elif roles["guard"] == 0:
                    print("平民数量不足，无法增加！")
                else:
                    print("守卫数量无法大于一个！")
            case "14":
                if roles["guard"] > 0:
                    roles["guard"] -= 1
                    roles["villgaer"] += 1
                else:
                    print("守卫数量不足，无法减少！")
            case "0":
                if good_guy > bad_guy:
                    break
                else:
                    print("好人数量太少了！至少要比坏人数量多一个！")
    return roles


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
