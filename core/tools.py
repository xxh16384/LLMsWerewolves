import json



def read_json(file_path):
    """
    读取一个json文件

    Args:
        file_path (str): json文件的路径

    Returns:
        dict: json文件的内容
    """
    with open(file_path,"r",encoding="UTF-8") as f:
        return json.load(f)


def extract_numbers_from_brackets(text):
    """
    在文本中查找所有的方括号，并将方括号之间的内容尝试
    转换为整数

    Args:
        text (str): 文本

    Returns:
        list: 文本中所有的数字
    """
    numbers = []

    # 查找文本中所有的“[” 和 “]”
    start = text.find('[')
    while start != -1:
        # 找到对应的"]"
        end = text.find(']', start)
        if end != -1:
            # 提取方括号之间的内容并尝试转换为整数
            try:
                number = int(text[start + 1:end])
                numbers.append(number)
            except ValueError:
                print(f"在位置 {start} 到 {end} 之间未找到有效的数字")
        else:
            print("找到了'['但没有对应的']'")
            break
        
        # 继续查找下一个"["
        start = text.find('[', end)

    return numbers


def find_max_key(vote_dict):
    """
    Finds the key with the maximum value in a dictionary.
    
    If there are multiple keys with the same maximum value, the first one
    encountered will be returned.
    
    Args:
        vote_dict (dict): The dictionary to search.
    
    Returns:
        object: The key with the maximum value.
    """
    max_value = max(vote_dict.values())
    max_keys = [k for k, v in vote_dict.items() if v == max_value]
    return max_keys[0] if len(max_keys) == 1 else 0
