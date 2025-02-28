from openai import OpenAI
import json
import logging
import os

def read_json(file_path):
    with open(file_path,"r",encoding="UTF-8") as f:
        return json.load(f)

def extract_numbers_from_brackets(text):
    # 初始化一个空列表来存储找到的数字
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

def get_all_players(t = "object"):
    if t == "object":
        return players
    elif t == "id":
        return [i.id for i in players]

def get_alive_werewolfs(t = "object"):
    if t == "object":
        return [i for i in players if i.role == "werewolf"]
    elif t == "id":
        return [i.id for i in players if i.role == "werewolf"]

def get_alive_players(t = "object"):
    if t == "object":
        return [i for i in players if i.alive]
    elif t == "id":
        return [i.id for i in players if i.alive]

def get_players_by_ids(ids:list):
    ids = [int(i) for i in ids]
    players_pending = [i for i in players if i.id in ids]
    if len(players_pending) > 1:
        return players_pending
    else:
        return players_pending[0]

class Context:
    contexts = []
    def __init__(self,source_id,content,visible_ids = []):
        self.source_id = source_id
        self.content = content
        self.visible_ids = set(visible_ids + [source_id] if visible_ids else [source_id])
        Context.contexts.append(self)
        logger.info(str(self))

    def get_context(id):
        pub_messages = []
        for i in Context.contexts:
            if id in i.visible_ids: #自己可见的
                pub_messages.append(str(i))
        return pub_messages

    def __str__(self):
        if self.source_id == 0:
            return f"上帝:{self.content}\n"
        return f"{self.source_id}号玩家:{self.content}\n"

class Player:
    def __init__(self,model:str,role:str,id:int):
        self.client = OpenAI(api_key = apis[model]["api_key"], base_url = apis[model]["base_url"])
        self.role = role
        self.id = id
        self.model = model
        self.alive = True
        self.messages = []
    
    def init_system_prompt(self):
        pre_instruction = f"你是{self.id}号玩家，" + pre_instructions[self.role]
        if self.role == "werewolf":
            wolfs = get_alive_werewolfs("id")
            pre_instruction += f"\n以下玩家是狼人{wolfs}，是你和你的队友"
        self.messages.append({"role":"system","content":pre_instruction})

    def get_response(self,prompt,if_pub):
        pub_messages = Context.get_context(self.id)
        prompt0 = prompt
        if if_pub:
            prompt = f"\n此前的公共信息如下：{str(pub_messages)}...注意：你现在在公共发言阶段，你的所有输出会被所有玩家听到，请直接口语化的输出你想表达的信息，不要暴露你的意图。（连括号中的内容也会被看到）" + prompt
        else:
            prompt = f"\n此前的公共信息如下：{str(pub_messages)}...注意：你现在在私聊阶段，你的输出只会被上帝听到。（如果你是狼人，你的聊天还会被同阵营的玩家听到）" + prompt
        self.messages.append({"role":"user","content":prompt})
        response = self.client.chat.completions.create(
            model = apis[self.model]["model_name"],
            messages = self.messages,
            stream = True
        )
        self.messages[-1]["content"] = prompt0

        # 处理回复
        collected_messages = ""
        reasoning_model = -1 # 判断是否是推理模型，-1待判断，0不是，1是
        print(f"玩家{self.id}（{self.role}）： ", end="", flush=True)
        for chunk in response:
            if reasoning_model == -1:
                try:
                    reasoning_message = chunk.choices[0].delta.reasoning_content
                    reasoning_model = 1
                    reasoning = True
                    print("思考中...\n", end="", flush=True)
                    print(reasoning_message, end="", flush=True)
                except:
                    reasoning_model = 0
            elif reasoning_model == 1:
                reasoning_message = chunk.choices[0].delta.reasoning_content
                chunk_message = chunk.choices[0].delta.content
                if reasoning_message and reasoning:
                    print(reasoning_message, end="", flush=True)
                elif not reasoning_message and reasoning and chunk_message:
                    print("\n思考结束...\n")
                    reasoning = False
                    collected_messages += chunk_message
                    print(chunk_message, end="", flush=True)
                elif not reasoning:
                    collected_messages += chunk_message
                    print(chunk_message, end="", flush=True)
            else:
                chunk_message = chunk.choices[0].delta.content
                collected_messages += chunk_message
                print(chunk_message, end="", flush=True)

        # 加入公共上下文
        if if_pub:
            Context(self.id,collected_messages,get_all_players("id"))
        else:
            if self.role == "werewolf":
                Context(self.id,collected_messages,get_alive_werewolfs("id"))
            else:
                Context(self.id,collected_messages)
        self.messages.append({"role":"assistant","content":collected_messages})

    def private_chat(self,source_id,content):
        if source_id == 0:
            self.get_response(f"上帝：{content}",False)
        else:
            self.get_response(f"{source_id}号玩家：{content}",False)

    def pub_chat(self,source_id,content):
        if source_id == 0:
            self.get_response(f"上帝：{content}",True)
        else:
            self.get_response(f"{source_id}号玩家：{content}",True)

    def __str__(self):
        return f"玩家{self.id}（{self.role}）"

def main():
    global pre_instructions
    global apis
    global players

    # 读取文件
    pre_instructions = read_json(instructions_path)
    apis = read_json(apis_path)
    players_info = read_json(players_info_path)

    # 初始化玩家信息
    players = []
    for i in players_info.keys():
        if i == "0":
            continue
        model = players_info[i]["model"]
        roles = players_info[i]["role"]
        players.append(Player(model,roles,int(i)))
    for i in players:
        i.init_system_prompt()
    Context(0,players_info["0"],get_all_players("id"))

    # 游戏主循环
    while True:
        ins = input("\n请输入指令:")
        try:
            if ins == "b":
                Context(0,input("请输入信息："),get_all_players("id"))
            elif ins == "exit":
                break
            elif ins == "pr":
                player_id = int(input("请输入玩家编号："))
                get_players_by_ids([player_id]).private_chat(0,input("请输入信息："))
            elif ins == "pu":
                player_id = int(input("请输入玩家编号："))
                get_players_by_ids([player_id]).pub_chat(0,input("请输入信息："))
            elif ins == "pu_batch":
                input_str = input("请输入群发玩家编号：")
                players_pending = get_players_by_ids(list(input_str.split(","))) if not input_str == "" else get_alive_players()
                content = input("请输入群发信息：")
                Context(0,content,get_all_players())
                for i in players_pending:
                    i.pub_chat(0,content)
            elif ins == "out":
                input_str = input("请输入群发玩家编号：")
                players_pending = get_players_by_ids(list(input_str.split(",")))
                for i in players_pending:
                    i.alive = False
            elif ins == "vote":
                input_str = input("请输入投票玩家编号：")
                players_pending = get_players_by_ids(list(input_str.split(","))) if not input_str == "" else get_alive_players()
                content = "请投票，投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以简短发言，解释投票理由。"
                Context(0,content,get_all_players())
                for i in players_pending:
                    i.pub_chat(0,content)
                result = {i.id:0 for i in players_pending}
                for i in players_pending:
                    voted = extract_numbers_from_brackets(i.messages[-1]['content'])
                    if voted and int(voted[-1]) in get_alive_players("id"):
                        result[int(voted[-1])] += 1
                logger.info(f"投票结果：{result}")
            elif ins == "wolf_discuss":
                pass
                input_str = input("请输入讨论玩家编号：")
                players_pending = get_players_by_ids(list(input_str.split(","))) if not input_str == "" else get_alive_werewolfs()
            elif ins == "print_context":
                for i in Context.contexts:
                    print(i,i.visible_ids)
            else:
                print("无效指令，请重新输入")
        except Exception as e:
            print(e)

if __name__ == "__main__":
    instructions_path = "instructions.json"
    apis_path = "apis.json"
    players_info_path = "player_info.json"
    game_name = input("请输入游戏名称：")
    
    if not os.path.exists("./log"):
        os.mkdir("./log")
    if not os.path.exists(f"./log/{game_name}.md"):
        with open(f"./log/{game_name}.md","w",encoding="UTF-8") as f:
            f.write("# " + game_name + "\n\n")

    logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(level = logging.INFO)
    handler = logging.FileHandler(f"./log/{game_name}.md",encoding="UTF-8")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('**%(asctime)s-%(levelname)s** \n%(message)s\n')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    main()