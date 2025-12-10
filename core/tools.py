import json


def read_json(file_path: str) -> dict:
    """读取并解析一个JSON文件。

    Args:
        file_path (str): JSON文件的路径。

    Returns:
        dict: 从JSON文件解析出的字典内容。
    """
    with open(file_path, "r", encoding="UTF-8") as f:
        return json.load(f)


def print_json(input_json: dict):
    """将字典以格式化的JSON字符串形式打印到控制台。

    Args:
        input_json (dict): 需要格式化打印的字典。
    """
    formatted_data = json.dumps(input_json, indent=4)
    print(formatted_data)


def extract_numbers_from_brackets(text: str) -> int | None:
    """从文本中提取所有由方括号包围的数字。

    此函数会查找文本中所有的方括号对 `[]`，并尝试将它们
    之间的内容转换为整数。

    Args:
        text (str): 待搜索的输入文本。

    Returns:
        list: 一个包含所有成功提取并转换的整数的列表。
    """
    numbers = []
    start = text.find("[")
    while start != -1:
        end = text.find("]", start)
        if end != -1:
            try:
                number = int(text[start + 1 : end])
                numbers.append(number)
            except ValueError:
                print(f"在位置 {start} 到 {end} 之间未找到有效的数字")
        else:
            print("找到了'['但没有对应的']'")
            break
        start = text.find("[", end)
    return numbers


def find_max_key(vote_dict: dict) -> int:
    """在字典中查找具有最大值的键。

    该函数用于在投票结果等场景中找出得票最多的键。如果存在多个
    键拥有相同的最大值（即平票），则返回0。

    Args:
        vote_dict (dict): 待搜索的字典，通常键为候选项，值为票数。

    Returns:
        object: 具有唯一最大值的键。如果出现平票，则返回0。
    """
    max_value = max(vote_dict.values())
    max_keys = [k for k, v in vote_dict.items() if v == max_value]
    return max_keys[0] if len(max_keys) == 1 else 0


def makeDic(array: list) -> dict:
    """根据对象列表创建一个以对象ID为键的字典。

    此函数遍历一个包含对象的列表，使用每个对象的 `id` 属性作为
    新字典的键，并将所有值初始化为0。常用于初始化计票器。

    Args:
        array (list): 一个包含具有 `id` <b>属性的对象的列表。

    Returns:
        dict: 一个键为对象ID，值为0的字典。
    """
    return {element.id: 0 for element in array}
