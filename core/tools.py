import json


def read_json(file_path):
    """
    读取一个json文件

    参数：
        file_path (str): json文件的路径

    返回：
        dict: json文件的内容
    """
    with open(file_path, "r", encoding="UTF-8") as f:
        return json.load(f)


def print_json(input_json):
    """
    格式化输出json文本
    """
    formatted_data = json.dumps(input_json, indent=4)
    print(formatted_data)


def extract_numbers_from_brackets(text):
    """
    在文本中查找所有的方括号，并将方括号之间的内容尝试
    转换为整数

    参数：
        text (str): 文本

    返回：
        list: 文本中所有的数字
    """
    numbers = []

    # 查找文本中所有的“[” 和 “]”
    start = text.find("[")
    while start != -1:
        # 找到对应的"]"
        end = text.find("]", start)
        if end != -1:
            # 提取方括号之间的内容并尝试转换为整数
            try:
                number = int(text[start + 1 : end])
                numbers.append(number)
            except ValueError:
                print(f"在位置 {start} 到 {end} 之间未找到有效的数字")
        else:
            print("找到了'['但没有对应的']'")
            break

        # 继续查找下一个"["
        start = text.find("[", end)

    return numbers


def find_max_key(vote_dict):
    """
    查找字典中具有最大值的键。

    如果有多个键具有相同的最大值，则返回第一个遇到的键。

    参数:
        vote_dict (dict): 要搜索的字典。

    返回:
        object: 具有最大值的键。
    """
    max_value = max(vote_dict.values())
    max_keys = [k for k, v in vote_dict.items() if v == max_value]
    return max_keys[0] if len(max_keys) == 1 else 0


def makeDic(array):
    return {element.id: 0 for element in array}
