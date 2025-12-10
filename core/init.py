import json
from .tools import read_json, print_json
from .general import *


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
        api_preset = "None"
        api_url = "None"
        api_key = "None"
        api_model = "None"
        while True:
            print(
                f"\n ————————————————————\
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
                    api_preset = input(
                        f"当前预设名字(自定义，仅用于和player对应，不可为-1)："
                    )
                    while api_preset == -1:
                        api_preset = input(
                            f"当前号预设名字(自定义，仅用于和player对应，不可为-1)："
                        )
                case "2":
                    api_url = input(f"当前号预设所使用api的url(请使用openai兼容格式)：")
                case "3":
                    api_key = input(
                        f"当前号预设所使用api的密钥(仅保存在本地，不会上传到云端)："
                    )
                case "4":
                    api_model = input(
                        f"当前号预设所使用api的模型(输出完整名字，输入-1以查询当前api所有模型(WIP))："
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
                    api_preset = "None"
                    api_url = "None"
                    api_key = "None"
                    api_model = "None"
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
        player_preset = "None"
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
                    player_preset = "None"
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
    def add_role(role):
        if roles["villager"] <= 0:
            return "平民数量不足，无法增加！"
        if role in ("seer", "witch", "guard") and roles[role] >= 1:
            return f"{PLAYERDIC[role]}的数量无法大于一个！"

        roles[role] += 1
        roles["villager"] -= 1
        return f"成功添加一个{PLAYERDIC[role]}。"

    def remove_role(role):
        if roles[role] <= 0:
            return f"{PLAYERDIC[role]}数量不足以减少！"
        if role in ("werewolf") and roles[role] <= 1:
            return f"至少要有一个{PLAYERDIC[role]}！"

        roles[role] -= 1
        roles["villager"] += 1
        return f"成功减少一个{PLAYERDIC[role]}"

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
        choice = input("请输入：")

        match (choice):
            case "1":
                print(add_role("werewolf"))
            case "2":
                print(add_role("seer"))
            case "3":
                print(add_role("witch"))
            case "4":
                print(add_role("guard"))
            case "11":
                print(remove_role("werewolf"))
            case "12":
                print(remove_role("seer"))
            case "13":
                print(remove_role("witch"))
            case "14":
                print(remove_role("guard"))
            case "0":
                if good_guy > bad_guy:
                    break
                else:
                    print("好人数量太少了！至少要比坏人数量多一个！")
    return roles
