import json
from .tools import read_json, print_json
from .general import *


def api_template_check(apis_path) -> None:
    """检查API模板配置文件是否存在，若不存在则引导用户创建。

    此函数首先尝试读取指定的API模板JSON文件。如果文件不存在或读取失败，
    它会启动一个交互式的命令行界面，引导用户逐条输入API预设信息，
    包括预设名称、URL、密钥和模型名称。用户可以添加多个预设，并
    在完成所有填写后，将配置信息保存到指定的路径中。

    Args:
        apis_path (str): API模板配置文件的路径。
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
                        "若有想要删除的api预set，在此输入那个预设的名字，否则输入-1。"
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


def api_players_check(apis_path, api_players_path) -> None:
    """检查玩家API配置文件是否存在，若不存在则引导用户创建。

    此函数首先尝试读取玩家API配置文件。如果文件不存在，它会启动一个
    交互式命令行界面，引导用户为游戏中的每一位玩家（从1号开始）分配
    一个在 `apis_path` 文件中定义好的API预设。完成所有玩家的分配后，
    配置将被写入指定的 `api_players_path` 文件。

    Args:
        apis_path (str): 已存在的API模板配置文件的路径，用于参考。
        api_players_path (str): 待创建或检查的玩家API配置文件的路径。
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
        players = {}
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


def roles_divided(api_players_path) -> dict:
    """根据玩家总数，通过交互式界面分配游戏角色。

    该函数首先从玩家配置文件中读取玩家总数，然后提供一个默认的角色配置。
    接着，它启动一个命令行界面，允许用户通过输入指令来增加或减少各种
    神职和狼人角色的数量，平民数量会相应自动调整。函数内置了逻辑来
    确保角色分配的合理性（如神职唯一性、好人阵营人数多于坏人等）。
    用户确认分配方案后，函数返回最终的角色配置。

    Args:
        api_players_path (str): 玩家API配置文件的路径，用于确定玩家总数。

    Returns:
        dict: 一个包含最终角色及其数量的字典。例如：
            {'werewolf': 3, 'seer': 1, 'witch': 1, 'guard': 1, 'villager': 4}
    """

    def add_role(role):
        if roles["villager"] <= 0:
            return "平民数量不足，无法增加！"
        if role in SINGLE_ROLE and roles[role] >= 1:
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

    def make_role(choice):
        if len(choice) == 1:
            role = ROLE_INDEX[choice]
            print(add_role(role))
        elif len(choice) == 2:
            choice = choice[1]
            role = ROLE_INDEX[choice]
            print(remove_role(role))
        else:
            print("无效输入。")

    def get_role_by_faction(faction):
        return [role for role in LEGAL_ROLE.keys() if LEGAL_ROLE[role] == faction]

    def roles_divided_string(role):
        if role == "villager":
            return f"[----]   平民   数量: {roles["villager"]:2d}"
        add_role_id = reverse_choices[role]
        remove_role_id = "1" + add_role_id
        role_length = len(PLAYERDIC[role])
        space_times = (10 - role_length * 2) // 2
        return f"[{add_role_id}/{remove_role_id}]{" "*space_times}{PLAYERDIC[role]}{" "*space_times}数量：{roles[role]:2d}"

    def count(therole):
        return sum([roles[role] for role in therole])

    players = read_json(api_players_path)
    counts = len(players)
    roles = {
        "werewolf": 3,
        "seer": 1,
        "witch": 1,
        "guard": 1,
        "hunter": 1,
        "villager": -1,
    }
    for role in LEGAL_ROLE.keys():
        if not role in roles:
            roles[role] = 0
    reverse_choices = {ROLE_INDEX[i]: i for i in ROLE_INDEX.keys()}
    bads = get_role_by_faction("bad")
    goods = get_role_by_faction("good")
    neutral = get_role_by_faction("neutral")
    special = bads + goods + neutral
    special.remove("villager")

    while True:
        roles["villager"] = counts - count(special)
        bad_guy = count(bads)
        good_guy = count(goods)
        neutral_guy = count(neutral)

        print(
            f"\n ——————————————————\
              \n 请输入这一局的职业划分，\
              \n [a/b]中，a代表加1人，b代表减1人"
        )
        for role in LEGAL_ROLE.keys():
            print(roles_divided_string(role))
        print(f"\n [0]    完成职业划分")

        choice = input("请输入：")

        if choice == "0":
            if good_guy > bad_guy + neutral_guy:
                break
            else:
                print("好人数量太少了！至少要比坏人加中立职业的数量多一个！")
        else:
            make_role(choice)

    for role in LEGAL_ROLE.keys():
        if roles[role] == 0:
            del roles[role]

    return roles


def role_json_made(roles: dict, doc_path: str, instructions_path: str) -> None:
    """读取这一局存在的角色职业划分，生成这一局游戏所使用的提示词。

    Args:
        roles (dict): 一个包含本局角色及其数量的字典。
        doc_path (str): 所有提示词的存放路径。
        instructions_path (str): 本局所用提示词文件的路径。
    """
    todo = []
    for key in roles.keys():
        if roles[key] >= 1:
            todo.append(key)

    roles_instruction = {}

    default = ""
    path = doc_path + "general/general.yaml"
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            default += line
    for role in todo:
        if not role in NORMAL_ROLE:
            path = doc_path + "general/" + role + ".yaml"
            with open(path, "r", encoding="utf-8") as file:
                for line in file:
                    default += line
    roles_instruction["general"] = default

    for role in todo:
        path = doc_path + role + ".yaml"
        result = ""
        with open(path, "r", encoding="utf-8") as file:
            for line in file:
                result += line
        roles_instruction[role] = result

    roles_json = json.dumps(roles_instruction, ensure_ascii=False, indent=4)

    with open(instructions_path, "w", encoding="utf-8") as f:
        f.write(roles_json)
