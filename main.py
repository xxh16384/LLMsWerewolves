from openai import OpenAI
import json
import logging

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

def get_all_players():
    return [i for i in range(1,len(roles)+1)]

def get_all_werewolfs():
    return [i for i in range(1,len(roles)+1) if roles[i-1] == "werewolf"]

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
        elif self.source_id == -1:
            return f"系统提示:{self.content}\n"
        return f"{self.source_id}号玩家:{self.content}\n"

class Player:
    def __init__(self,model,role,id):
        self.client = OpenAI(api_key = apis[model]["api_key"], base_url = apis[model]["base_url"])
        self.role = role
        self.id = id
        self.model = model
        self.alive = True
        self.messages = []
        pre_instruction = f"你是{id}号玩家，" + pre_instructions[role]
        if role == "werewolf":
            wolf_index = [i + 1 for i,val in enumerate(roles) if val=="werewolf"]
            pre_instruction += f"\n编号为{wolf_index}的玩家都是狼人，是你的队友"
        self.messages.append({"role":"system","content":pre_instruction})

    def get_response(self,prompt,if_pub):
        pub_messages = Context.get_context(self.id)
        print(f"\n玩家{self.id}： ", end="", flush=True)
        prompt0 = prompt
        if if_pub:
            prompt = f"\n此前的公共信息如下：{str(pub_messages)}...注意：你现在在公共发言阶段，你的所有输出会被所有玩家听到，请直接口语化的输出你想表达的信息，不要暴露你的意图。（连括号中的内容也会被看到）" + prompt
        else:
            prompt = f"\n此前的公共信息如下：{str(pub_messages)}...注意：你现在在私聊阶段，你的输出只会被上帝听到。（如果你是狼人，你的聊天还会被同阵营的玩家听到）" + prompt
        self.messages.append({"role":"user","content":prompt})
        prompt = ""
        response = self.client.chat.completions.create(
            model = apis[self.model]["model_name"],
            messages = self.messages,
            stream = True
        )
        self.messages[-1]["content"] = prompt0

        # 处理回复
        collected_messages = ""
        if self.model == "deepseek-r1":
            print(f"正在思考： ", end="", flush=True)
            reasoning = True
        else:
            reasoning = False
        for chunk in response:
            if self.model == "deepseek-r1" and chunk.choices[0].delta.reasoning_content:
                chunk_message = chunk.choices[0].delta.reasoning_content
                print(chunk_message, end="", flush=True)
            if chunk.choices[0].delta.content:
                if reasoning:
                    reasoning = False
                    print("\n思考结束...\n")
                chunk_message = chunk.choices[0].delta.content
                collected_messages += chunk_message
                print(chunk_message, end="", flush=True)

        # 加入公共上下文
        if if_pub:
            Context(self.id,collected_messages,get_all_players())
        else:
            if self.role == "werewolf":
                Context(self.id,collected_messages,get_all_werewolfs())
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

def main():
    global pre_instructions
    global apis
    pre_instructions = read_json(instructions_path)
    apis = read_json(apis_path)
    players = []
    for i in range(len(roles)):
        players.append(Player("deepseek-r1",roles[i],i+1))
    Context(0,"这是一局有7个玩家的狼人杀，分别有2个狼人，3个村民，一个预言家和一个女巫",get_all_players())
    while True:
        ins = input("\n请输入指令:")
        try:
            if ins == "b":
                Context(0,input("请输入信息："),get_all_players())
            elif ins == "exit":
                break
            elif ins == "pr":
                player_id = int(input("请输入玩家编号："))
                players[player_id-1].private_chat(0,input("请输入信息："))
            elif ins == "pu":
                player_id = int(input("请输入玩家编号："))
                players[player_id-1].pub_chat(0,input("请输入信息："))
            elif ins == "pu_batch":
                input_str = input("请输入群发玩家编号：")
                player_ids = [int(i) for i in input_str.split(",")] if not input_str == "" else [i for i in range(1,len(roles)+1) if players[i-1].alive]
                content = input("请输入群发信息：")
                for i in player_ids:
                    players[i-1].pub_chat(0,content)
            elif ins == "out":
                player_ids = [int(i) for i in input("请输入出局玩家编号：").split(",")]
                for i in player_ids:
                    players[i-1].alive = False
            elif ins == "vote":
                input_str = input("请输入投票玩家编号：")
                player_ids = [int(i) for i in input_str.split(",")] if not input_str == "" else [i for i in range(1,len(roles)+1) if players[i-1].alive]
                content = "请投票，投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以简短发言，解释投票理由。"
                for i in player_ids:
                    players[i-1].pub_chat(0,content)
                result = {i:0 for i in player_ids}
                for i in player_ids:
                    voted = extract_numbers_from_brackets(players[i-1].messages[-1]['content'])
                    if voted and int(voted[0]) in player_ids:
                        result[int(voted[0])] += 1
                logger.info(f"投票结果：{result}")
            elif ins == "wolf_discuss":
                input_str = input("请输入讨论玩家编号：")
                player_ids = [int(i) for i in input_str.split(",")] if not input_str == "" else [i for i in range(1,len(roles)+1) if players[i-1].role == "werewolf"]
            elif ins == "print_context":
                for i in Context.contexts:
                    print(i,i.visible_ids)
            else:
                print("无效指令，请重新输入")
        except Exception as e:
            print(e)

if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(level = logging.INFO)
    handler = logging.FileHandler("log.md",encoding="UTF-8")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('**%(asctime)s-%(levelname)s** \n```\n%(message)s```\n\n')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


    instructions_path = "instructions.json"
    apis_path = "apis.json"
    roles = ["werewolf"]*2 + ["villager"]*3 + ["witch", "seer"]
    # -1为系统提示词，0为上帝，1、2狼人，3、4、5村民，6女巫，7预言家
    game_name = input("请输入游戏名称：")
    logger.info(game_name)

    main()