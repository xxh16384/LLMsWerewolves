from openai import OpenAI
import json
import re

instructions_path = "instructions.json"
apis_path = "apis.json"
roles = ["werewolf"]*2 + ["villager"]*3 + ["witch", "seer"]
# 0为上帝，1、2狼人，3、4、5村民，6女巫，7预言家

def read_json(file_path):
    with open(file_path,"r",encoding="UTF-8") as f:
        return json.load(f)

def extract_bracket_content(text):
    # 使用正则表达式查找所有符合模式的字符串
    matches = re.findall(r'$(\d+)$', text)
    return matches

pub_messages = []
def broadcast(source_id,content):
    if source_id == 0:
        pub_messages.append(f"上帝：{content}")
    else:
        pub_messages.append(f"{source_id}号玩家：{content}")

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
        self.prompt = pre_instruction

    def get_response(self,if_pub):
        prompt0 = self.prompt
        if if_pub:
            self.prompt = f"\n此前的公共信息如下：{str(pub_messages)}...注意：你现在在公共发言阶段，你的所有输出会被所有玩家听到，请直接口语化的输出你想表达的信息，不要暴露你的意图。（连括号中的内容也会被看到）" + self.prompt
        else:
            self.prompt = f"\n此前的公共信息如下：{str(pub_messages)}...注意：你现在在私聊阶段，你的输出只会被同阵营的玩家以及上帝听到。" + self.prompt
        self.messages.append({"role":"user","content":self.prompt})
        self.prompt = ""
        response = self.client.chat.completions.create(
            model = apis[self.model]["model_name"],
            messages = self.messages,
            stream = True
        )
        # 不让公共信息占用太多的上下文
        self.messages[-1]["content"] = prompt0

        collected_messages = ""
        if self.model == "deepseek-r1":
            print(f"\n玩家{self.id}正在思考： ", end="", flush=True)
            reasoning = True
        else:
            reasoning = False
        for chunk in response:
            # 使用 .choices 属性访问内容
            if self.model == "deepseek-r1" and chunk.choices[0].delta.reasoning_content:
                chunk_message = chunk.choices[0].delta.reasoning_content
                print(chunk_message, end="", flush=True)
            if chunk.choices[0].delta.content:
                if reasoning:
                    reasoning = False
                    print("\n思考结束...\n")
                chunk_message = chunk.choices[0].delta.content
                collected_messages += chunk_message
                print(chunk_message, end="", flush=True)  # 实时打印生成的内容

        self.messages.append({"role": "assistant", "content": collected_messages})
        if if_pub:
            broadcast(self.id,collected_messages)

    def private_chat(self,source_id,content):
        if source_id == 0:
            self.prompt += f"上帝：{content}"
        else:
            self.prompt += f"{source_id}号玩家：{content}"
        self.get_response(False)
    
    def pub_chat(self,source_id,content):
        if source_id == 0:
            self.prompt += f"上帝：{content}"
        else:
            self.prompt += f"{source_id}号玩家：{content}"
        broadcast(source_id,content)
        self.get_response(True)

def main():
    global pre_instructions
    global apis
    pre_instructions = read_json(instructions_path)
    apis = read_json(apis_path)
    players = []
    for i in range(len(roles)):
        players.append(Player("qwen-max",roles[i],i+1))
    broadcast(0,"这是一局有7个玩家的狼人杀，分别有2个狼人，3个村民，一个预言家和一个女巫")
    while True:
        ins = input("\n请输入指令:")
        try:
            if ins == "b":
                broadcast(0,input("请输入信息："))
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
                content = "请投票，投票结果用[]包围，其中只包含编号数字，例如[1]"
                for i in player_ids:
                    players[i-1].pub_chat(0,content)
                for i in player_ids:
                    
                    players[i-1].messages[-1]
            else:
                print("无效指令，请重新输入")
        except Exception as e:
            print(e)

main()