# 时间对应表，不建议改变
TIMEDIC = {1: "白天", 0: "晚上"}

# 当前程序中，可以选择的职业以及对应的阵营
LEGAL_ROLE = {
    "villager": "good",
    "werewolf": "bad",
    "seer": "good",
    "witch": "good",
    "guard": "good",
    "hunter": "good",
    "joker": "neutral",
    "whitewolf": "bad",
}

# 职业索引，在开局定义职业时，每个职业对应的编号
# 暂时只支持1位键值。如果数字不够，可以使用字母。
ROLE_INDEX = {
    "0": "villager",
    "1": "werewolf",
    "2": "seer",
    "3": "witch",
    "4": "guard",
    "5": "hunter",
    "6": "joker",
    "7": "fool",
    "8": "whitewolf",
}

# 玩家对应表，用于输出每个职业的中文名
# 如果你设计了新的职业，建议你在这里写下它们对应的中文名字，不会发送给AI
PLAYERDIC = {
    "werewolf": "狼人",
    "villager": "平民",
    "witch": "女巫",
    "seer": "预言家",
    "guard": "守卫",
    "hunter": "猎人",
    "joker": "小丑",
    "fool": "傻子",
    "whitewolf": "白狼",
}
# 只能存在一个的职业
SINGLE_ROLE = [
    "seer",
    "witch",
    "guard",
    "joker",
    "whitewolf",
]

# 简单的职业，不需要通用提示词
NORMAL_ROLE = [
    "villager",
    "werewolf",
]
