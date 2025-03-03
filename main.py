from openai import OpenAI
import json
import logging
import os


def set_logger(game_name):
    if not os.path.exists("./log"):
        os.mkdir("./log")
    if not os.path.exists(f"./log/{game_name}.md"):
        with open(f"./log/{game_name}.md","w",encoding="UTF-8") as f:
            f.write("# " + game_name + "\n\n")

    # 设置日志记录器
    logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(level = logging.INFO)
    handler = logging.FileHandler(f"./log/{game_name}.md",encoding="UTF-8")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('**%(asctime)s-%(levelname)s** \n%(message)s\n')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = set_logger("test")
instructions_path = "instructions.json"
apis_path = "apis.json"
players_info_path = "player_info.json"

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

def get_players(t = "object",alive = True , role = "all"):
    if role == "all":
        if alive:
            if t == "object":
                return [i for i in Player.players if i.alive]
            elif t == "id":
                return [i.id for i in Player.players if i.alive]
        else:
            if t == "object":
                return Player.players
            elif t == "id":
                return [i.id for i in Player.players]
    else:
        if alive:
            if t == "object":
                return [i for i in Player.players if i.role == role and i.alive]
            elif t == "id":
                return [i.id for i in Player.players if i.role == role and i.alive]
        else:
            if t == "object":
                return [i for i in Player.players if i.role == role]
            elif t == "id":
                return [i.id for i in Player.players if i.role == role]

def get_players_by_ids(ids:list):
    ids = [int(i) for i in ids]
    players_pending = [i for i in Player.players if i.id in ids]
    return players_pending

class Context:
    contexts = []
    def __init__(self,source_id,content,visible_ids = []):
        self.source_id = source_id
        self.content = content
        self.visible_ids = set(visible_ids + [source_id,0] if visible_ids else [source_id,0])
        Context.contexts.append(self)
        logger.info(str(self))

    def get_context(id):
        pub_messages = []
        for i in Context.contexts:
            if id in i.visible_ids: #自己可见的
                pub_messages.append(str(i))
        return pub_messages

    def __str__(self):
        v_id = self.visible_ids
        v_id.discard(0)
        if self.source_id == 0:
            return f"上帝:{self.content}（{v_id}可见）\n"
        return f"{get_players_by_ids([self.source_id])[0]}:{self.content}（{v_id}可见）\n"

class Player:

    players = []
    apis = {}

    def __init__(self,model:str,role:str,id:int,apis:dict):
        self.client = OpenAI(api_key = apis[model]["api_key"], base_url = apis[model]["base_url"])
        self.role = role
        self.id = id
        self.model = model
        self.alive = True
        self.messages = []
        if self.role == "witch":
            self.poison = False
            self.antidote = False
        Player.players.append(self)
        Player.apis = apis

    def init_system_prompt(self,pre_instructions:dict):
        pre_instruction = f"你是{self.id}号玩家，" + pre_instructions[self.role]
        if self.role == "werewolf":
            wolfs = get_players("id",alive=False,role="werewolf")
            pre_instruction += f"\n以下玩家是狼人{wolfs}，是你和你的队友"
        self.messages.append({"role":"system","content":pre_instruction})

    def get_response(self,prompt,if_pub):
        pub_messages = Context.get_context(self.id)
        prompt0 = prompt
        if if_pub:
            prompt = f"\n此前你能得知的玩家发言以及公共信息如下：{str(pub_messages)}...注意：你现在在公共发言阶段，你的所有输出会被所有玩家听到，请直接口语化的输出你想表达的信息，不要暴露你的意图。（连括号中的内容也会被看到）" + prompt
        else:
            prompt = f"\n此前你能得知的玩家发言以及公共信息如下：{str(pub_messages)}...注意：你现在在私聊阶段，你的输出只会被上帝听到。（如果你是狼人，你的聊天还会被同阵营的玩家听到）" + prompt
        self.messages.append({"role":"user","content":prompt})
        response = self.client.chat.completions.create(
            model = Player.apis[self.model]["model_name"],
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

        print("")

        # 加入公共上下文
        if if_pub:
            Context(self.id,collected_messages,get_players("id",alive=False))
        else:
            if self.role == "werewolf":
                Context(self.id,collected_messages,get_players("id",role="werewolf"))
            else:
                Context(self.id,collected_messages)
        self.messages.append({"role":"assistant","content":collected_messages})

    def private_chat(self,source_id,content):
        if source_id == 0:
            Context(0,f"上帝：{content}",[self.id])
            self.get_response(f"上帝：{content}",False)
        else:
            Context(source_id,f"{source_id}号玩家：{content}",[self.id])
            self.get_response(f"{source_id}号玩家：{content}",False)

    def pub_chat(self,source_id,content):
        if source_id == 0:
            self.get_response(f"上帝：{content}",True)
        else:
            self.get_response(f"{source_id}号玩家：{content}",True)

    def __str__(self):
        return f"玩家{self.id}（{self.role}）"

def init_game(players_info, apis, pre_instructions):
    for i in players_info.keys():
        if i == "0":
            continue
        model = players_info[i]["model"]
        roles = players_info[i]["role"]
        Player(model,roles,int(i),apis)
    for i in Player.players:
        i.init_system_prompt(pre_instructions)
    Context(0,players_info["0"],get_players(t="id",alive=False))

def find_max_key(vote_dict):
    max_value = max(vote_dict.values())
    max_keys = [k for k, v in vote_dict.items() if v == max_value]
    return max_keys[0] if len(max_keys) == 1 else 0

def vote():
    players_pending = get_players()
    content = "请投票，投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以简短发言，解释投票理由。"
    Context(0,content,get_players(t="id",alive=False))
    for i in players_pending:
        i.pub_chat(0,content)
    result = {i.id:0 for i in players_pending}
    for i in players_pending:
        voted = extract_numbers_from_brackets(i.messages[-1]['content'])
        if voted and int(voted[-1]) in get_players("id"):
                        result[int(voted[-1])] += 1
    return result

def public_discussion():
    players_pending = get_players()
    content = "请公开讨论，在此阶段你可以简短发言，解释讨论理由。"
    Context(0,content,get_players(t="id",alive=False))
    for i in players_pending:
        i.pub_chat(0,content)

def werewolf_killing():
    players_pending = get_players(role="werewolf")
    if not players_pending:
        return
    content = "今晚你想杀谁？"
    for i in players_pending:
        i.private_chat(0,content)
    content = "请进行杀人投票，杀人投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以自由发言解释杀人理由。"
    for i in players_pending:
        i.private_chat(0,content)
    result = {i.id:0 for i in get_players()}
    for i in players_pending:
        voted = extract_numbers_from_brackets(i.messages[-1]['content'])
        if voted and int(voted[-1]) in get_players("id"):
            result[int(voted[-1])] += 1
    killed = find_max_key(result)
    if killed:
        Context(0,f"今晚{killed}号玩家被杀了",get_players(t="id",role="werewolf",alive=False))
        return killed
    else:
        Context(0,f"击杀失败",get_players(t="id",role="werewolf",alive=False))
        return 0

def seer_seeing():
    seer=get_players(role="seer",alive=False)[0]
    if not seer.alive:
        return
    seer.private_chat(0,"你今晚要查谁？要查询的玩家编号请用[]包围，例如'我要查询[7]号玩家'。可以简短的给出理由。")
    target = extract_numbers_from_brackets(seer.messages[-1]['content'])
    seer.private_chat(0,f"你今晚要查的玩家是{get_players_by_ids(target)[0]}，他的身份是{get_players_by_ids(target)[0].role}")

def witch_operation(death_today):
    witch = get_players(role="witch",alive=False)[0]
    if not witch.alive:
        return
    if death_today:
        if not witch.poison and not witch.antidote:
            witch.private_chat(0,f"今晚{death_today}号玩家被杀了，你可以选择救他或者不救，选择结果用[]包围，救请写[1]，不救请写[0]，你可以简短的给出理由。另外，你今晚还有毒药，如果不救，你可以选择毒杀别人，如果不救，是否毒杀将在下一条消息中选择，本次回复无需选择，只需要回答救或者不救这一问题。")
            voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
            if voted and int(voted[-1]) == 1:
                witch.antidote = True
                Context(0,f"今晚{death_today}号玩家被杀了，你选择了救他",get_players(t="id",alive=False,role="witch"))
                get_players_by_ids([death_today])[0].alive = True
            else:
                Context(0,f"今晚{death_today}号玩家被杀了，你选择了不救他",get_players(t="id",alive=False,role="witch"))
                witch.private_chat(0,f"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。")
                voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                if int(voted[-1]):
                    witch.poison = True
                    Context(0,f"今晚{death_today}号玩家被杀了，你选择了毒杀{int(voted[-1])}号玩家",get_players(t="id",alive=False,role="witch"))
                    get_players_by_ids([int(voted[-1])])[0].alive = False
                else:
                    Context(0,f"今晚{death_today}号玩家被杀了，你选择了不毒杀",get_players(t="id",alive=False,role="witch"))
        elif not witch.antidote and witch.poison:
            witch.private_chat(0,f"今晚{death_today}号玩家被杀了，你可以选择救他或者不救，选择结果用[]包围，救请写[1]，不救请写[0]，你可以简短的给出理由。另外，你今晚没有毒药了。")
            voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
            if voted and int(voted[-1]) == 1:
                witch.antidote = True
                Context(0,f"今晚{death_today}号玩家被杀了，你选择了救他",get_players(t="id",alive=False,role="witch"))
                get_players_by_ids([death_today])[0].alive = True
        elif witch.antidote and not witch.poison:
            witch.private_chat(0,"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。")
            voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
            if int(voted[-1]):
                witch.poison = True
                Context(0,f"你选择了毒杀{int(voted[-1])}号玩家",get_players(t="id",alive=False,role="witch"))
                get_players_by_ids([int(voted[-1])])[0].alive = False
            else:
                Context(0,f"你选择了不毒杀",get_players(t="id",alive=False,role="witch"))
        else:
            pass
    else:
        if not witch.poison:
            witch.private_chat(0,"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。")
            voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
            if int(voted[-1]):
                witch.poison = True
                Context(0,f"你选择了毒杀{int(voted[-1])}号玩家",get_players(t="id",alive=False,role="witch"))
                get_players_by_ids([int(voted[-1])])[0].alive = False
            else:
                Context(0,f"你选择了不毒杀",get_players(t="id",alive=False,role="witch"))
        else:
            pass

def game_over():
    if len(get_players(alive=True)) - 2*len(get_players(alive=True,role="werewolf")) < 0: # 好人数量小于狼人数量
        Context(0,f"游戏结束，狼人获胜",get_players(t="id",alive=False))
        return 1
    elif len(get_players(alive=True,role="werewolf")) == 0:
        Context(0,f"游戏结束，好人获胜",get_players(t="id",alive=False))
        return 1
    else:
        return 0


def auto():

    # 读取文件
    pre_instructions = read_json(instructions_path)
    apis = read_json(apis_path)
    players_info = read_json(players_info_path)

    init_game(players_info, apis, pre_instructions)

    days = 0

    # 游戏主循环
    while len(get_players(alive=True)) > 0:
        players_id_before_night = set(get_players(t="id",alive=True))
        Context(0,f"现在是第{days+1}天，天黑请闭眼。",get_players(t="id",alive=False))
        killed_tonight =werewolf_killing()
        if killed_tonight:
            get_players_by_ids([killed_tonight])[0].alive = False
        seer_seeing()
        witch_operation(killed_tonight)
        death_tonight = players_id_before_night - set(get_players(t="id",alive=True))
        if len(death_tonight) > 0:
            Context(0,f"天亮了，今晚{list(death_tonight)}号玩家被杀了，出局。",get_players(t="id",alive=False))
        else:
            Context(0,f"天亮了，今晚是个平安夜，没有人死亡。",get_players(t="id",alive=False))
        if game_over():
            break
        public_discussion()
        vote_result = vote()
        out = find_max_key(vote_result)
        if out > 0:
            Context(0,f"投票结果是{out}号玩家出局，身份是{get_players_by_ids([int(out)])[0].role}",get_players(t="id",alive=False))
            get_players_by_ids([out])[0].alive = False
            get_players_by_ids([out])[0].pub_chat(0,f"你被投票出局了，请发表遗言。")
        else:
            Context(0,f"没有人被投票出局。",get_players(t="id",alive=False))
        days += 1
        if game_over():
            break
    
    players_pending = get_players(alive=False)
    content = "请发表复盘感想"
    Context(0,content,get_players(t="id",alive=False))
    for i in players_pending:
        i.pub_chat(0,content)
    Context(0,f"游戏结束",get_players(t="id",alive=False))

def main():
    global pre_instructions
    global apis

    # 读取文件
    pre_instructions = read_json(instructions_path)
    apis = read_json(apis_path)
    players_info = read_json(players_info_path)

    init_game(players_info)

    # 游戏主循环
    while True:
        ins = input("\n请输入指令:")
        try:
            if ins == "b":
                Context(0,input("请输入信息："),get_players(t="id",alive=False))
            elif ins == "exit":
                break
            elif ins == "pr":
                player_id = int(input("请输入玩家编号："))
                get_players_by_ids([player_id])[0].private_chat(0,input("请输入信息："))
            elif ins == "pu":
                player_id = int(input("请输入玩家编号："))
                get_players_by_ids([player_id])[0].pub_chat(0,input("请输入信息："))
            elif ins == "pu_batch":
                input_str = input("请输入群发玩家编号：")
                players_pending = get_players_by_ids(list(input_str.split(","))) if not input_str == "" else get_players()
                content = input("请输入群发信息：")
                Context(0,content,get_players(alive=False))
                for i in players_pending:
                    i.pub_chat(0,content)
            elif ins == "pub_discuss":
                public_discussion()
            elif ins == "out":
                input_str = input("请输入出局玩家编号：")
                players_pending = get_players_by_ids(list(input_str.split(",")))
                for i in players_pending:
                    i.alive = False
            elif ins == "vote":
                result = vote()
                logger.info(f"投票结果：{result}")
                out = find_max_key(result)
                if out == 0:
                    Context(0,"投票失败无人出局",get_players(t="id",alive=False))
                else:
                    players_pending = get_players_by_ids([out])
                    for i in players_pending:
                        i.alive = False
                        Context(0,f"{i.id}号玩家出局",get_players(t="id",alive=False))
            elif ins == "wolf_kill":
                result = werewolf_killing()
                logger.info(f"杀人结果：{result}")
                out = find_max_key(result)
                if out == 0:
                    Context(0,f"杀人失败无人出局",get_players(t="id",alive=False,role="werewolf"))
                else:
                    Context(0,f"确认{out}号玩家被杀",get_players(t="id",alive=False,role="werewolf"))
            elif ins == "print_context":
                for i in Context.contexts:
                    print(i)
            else:
                print("无效指令，请重新输入")
        except Exception as e:
            print(e)

if __name__ == "__main__":
    # 输入路径配置
    instructions_path = "instructions.json"
    apis_path = "apis.json"
    players_info_path = "player_info.json"
    game_name = input("请输入游戏名称：")

    # 创建日志文件
    logger = set_logger(game_name)

    auto()