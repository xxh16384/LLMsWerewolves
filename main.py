from openai import OpenAI
import json
import logging
import os
from time import sleep, time
import re

# 工具函数
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


class Context:
    contexts = {}
    def __init__(self,game,source_id,content,visible_ids = [],is_streaming = False, last_block = False):
        """
        保存游戏中的一个信息

        Args:
            game (Game): 游戏对象
            source_id (int): 信息的来源id
            content (str): 信息的内容
            visible_ids (list, optional): 可以看到这个信息的玩家id列表. Defaults to [].
        """

        if game not in Context.contexts.keys():
            Context.contexts[game] = []
        
        streaming = False if last_block else True
        if is_streaming:
            pre_block = Context.contexts[game][-1]
            if pre_block.source_id == source_id and pre_block.is_streaming and not pre_block.last_block:
                # 说明和前一条是一个人说的，则更新最后一条
                content = pre_block.content + content
                Context.contexts[game].pop(-1)
        Context.contexts[game].append(self)
        self.game = game
        self.stage = game.stage
        self.is_streaming = is_streaming
        self.last_block = last_block
        self.source_id = source_id
        self.content = content
        self.visible_ids = set(visible_ids + [source_id,0] if visible_ids else [source_id,0])

        if self.game:
            if not streaming:
                self.game.logger.info(self.__str__())
            # 强制触发日志更新（关键改进点）
            if hasattr(self.game, 'streamlit_log_trigger'):
                self.game.streamlit_log_trigger.set()

    def get_context(id,game):
        """
        根据玩家id和游戏id，返回该玩家可以看到的所有信息

        Args:
            id (int): 玩家id
            game (int): 游戏id

        Returns:
            list: 该玩家可以看到的所有信息
        """
        pub_messages = []
        for i in Context.contexts[game]:
            if id in i.visible_ids: #自己可见的
                pub_messages.append(re.sub(r'<think>.*?</think>', '', str(i), flags=re.DOTALL))
        return pub_messages
    
    def get_chat_log(game, stage):
        """
        根据游戏id和阶段，返回该阶段所有信息

        Args:
            game (int/str): 游戏唯一标识符，用于从上下文中获取对应游戏的记录
            stage (int/str): 需要过滤的特定阶段标识符

        Returns:
            list: 包含所有符合条件消息对象的列表，若无匹配项则返回空列表
        """
        messages = []
        # 遍历指定游戏的全部上下文记录
        for i in Context.contexts[game]:
            # 筛选出阶段标识匹配的记录
            if i.stage == stage:
                messages.append(i)
        return messages

    def __str__(self):
        v_id = self.visible_ids
        v_id.discard(0)
        if self.source_id == 0:
            return f"上帝:{self.content}（{v_id}可见）\n"
        return f"{self.source_id}号玩家:{self.content}（{v_id}可见）\n"

class Player:
    def __init__(self, role:str, id:int, game):
        """
        Initializes a Player instance with the given model, role, id, and game context.

        Args:
            model (str): The model identifier used for the player, corresponding to an API configuration.
            role (str): The role assigned to the player in the game (e.g., werewolf, villager, witch).
            id (int): The unique identifier for the player.
            game: The game context in which the player is participating.

        Attributes:
            game: The game context passed during initialization.
            client: An instance of OpenAI client configured with the player's model.
            role (str): The role of the player in the game.
            id (int): The unique identifier of the player.
            model (str): The model identifier used for the player.
            alive (bool): A flag indicating whether the player is currently alive (default is True).
            messages (list): A list of messages associated with the player.
            poison (bool): A flag indicating the availability of poison for the witch role (default is False).
            antidote (bool): A flag indicating the availability of antidote for the witch role (default is False).
        """

        self.game = game
        # self.client = OpenAI(api_key = game.apis["Model abbreviation"]["api_key"], base_url = game.apis["Model abbreviation"]["base_url"])
        self.client = game.client
        self.role = role
        self.id = id
        self.alive = True
        self.messages = []
        if self.role == "witch":
            self.poison = False
            self.antidote = False
        game.players.append(self)

    def init_system_prompt(self):
        """
        Initializes the system prompt for a player based on their role and game context.

        This method constructs a pre-instruction message for the player, indicating their
        role in the game and any relevant information specific to their role. If the player's
        role is 'werewolf', additional information about other werewolf players is included.

        The constructed message is appended to the player's message list as a system message.

        Side Effects:
            Updates the player's message list with a new system message containing the
            role-specific instructions and information.

        Attributes:
            pre_instruction (str): The instruction message constructed for the player.
            wolfs (list): A list of non-alive werewolf players, used to provide additional
                        information for players with the 'werewolf' role.
        """

        pre_instruction = f"你是{self.id}号玩家，" + self.game.instructions[self.role]
        if self.role == "werewolf":
            wolfs = self.game.get_players("id",alive=False,role="werewolf")
            pre_instruction += f"\n以下玩家是狼人{str(wolfs)[1:-1]}，是你和你的队友"
        self.messages.append({"role":"system","content":pre_instruction})

    def get_response(self,prompt,if_pub):
        """
        Simulates a conversation with the player, given a prompt and whether the response should be public.

        This method is used to get a response from the player in both the night and day phases of the game.
        When the response should be public, the player is shown all publicly available messages before being asked
        to respond. When the response should not be public, the player is shown all messages they can see, but
        their response is not shared with other players.

        The player's response is appended to the game's context as a new message, and the response is also returned
        by this method.

        Parameters:
            prompt (str): The prompt to be given to the player, which is used as the input for the AI model.
            if_pub (bool): Whether the response should be public (True) or private (False).

        Returns:
            str: The player's response to the prompt.

        Side Effects:
            The player's response is appended to the game's context as a new message.
        """
        
        sleep(1)
        
        visible_ids = self.game.get_players("id",alive=False) if if_pub else [self.id,0] + self.game.get_players("id",role=self.role)
        pub_messages = Context.get_context(self.id,self.game)
        prompt0 = prompt
        if if_pub:
            prompt = f"\n此前你能得知的玩家发言以及公共信息如下：{str(pub_messages)}...注意：你现在在公共发言阶段，你的所有输出会被所有玩家听到，请直接口语化的输出你想表达的信息，不要暴露你的意图。（连括号中的内容也会被看到）" + prompt
        else:
            prompt = f"\n此前你能得知的玩家发言以及公共信息如下：{str(pub_messages)}...注意：你现在在私聊阶段，你的输出只会被上帝听到。（如果你是狼人，你的聊天还会被同阵营的玩家听到）" + prompt
        self.messages.append({"role":"user","content":prompt})
        
        # print(f"{self} 的上下文： {self.messages}")
        
        response = self.client.chat.completions.create(
            model = self.game.apis["Model abbreviation"]["model_name"],
            messages = self.messages,
            stream = True
        )
        self.messages[-1]["content"] = prompt0

        # 处理回复
        collected_messages = ""
        reasoning_messages = ""
        reasoning_model = -1 # 判断是否是推理模型，-1待判断，0不是，1是
        print(f"玩家{self.id}（{self.role}）： ", end="", flush=True)
        for chunk in response:
            if reasoning_model == -1:
                try:
                    reasoning_message = chunk.choices[0].delta.reasoning_content
                    reasoning_messages += reasoning_message
                    reasoning_model = 1
                    reasoning = True
                    print("思考中...\n", end="", flush=True)
                    print(reasoning_message, end="", flush=True)
                except:
                    reasoning_model = 0
                    chunk_message = chunk.choices[0].delta.content
                    collected_messages += chunk_message
                    print(chunk_message, end="", flush=True)
            elif reasoning_model == 1:
                reasoning_message = chunk.choices[0].delta.reasoning_content
                chunk_message = chunk.choices[0].delta.content
                if reasoning_message and reasoning:
                    reasoning_messages += reasoning_message
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
        collected_messages = "<think>"+reasoning_messages+"</think>" + collected_messages if reasoning_messages else collected_messages
        Context(self.game,self.id,collected_messages,visible_ids)


        self.messages.append({"role":"assistant","content":collected_messages})

    def private_chat(self,source_id,content):
        """
        Allows a player to send a private chat message to another player.

        Args:
            source_id (int): The ID of the player sending the message.
            content (str): The content of the chat message to be sent.
        """
        
        if source_id == 0:
            Context(self.game,0,f"{content}",[self.id])
            # if not self.game.webui_mode:
            #     print(f"上帝：{content}")
            self.get_response(f"上帝：{content}",False)
        else:
            Context(self.game,source_id,f"{content}",[self.id])
            if not self.game.webui_mode:
                print(f"{source_id}号玩家：{content}")
            self.get_response(f"{source_id}号玩家：{content}",False)

    def pub_chat(self,source_id,content,add_to_context = True):
        """
        Handles public chat messages within the game context.

        This method allows a player or the system (represented by source_id = 0) to send
        a public chat message to all players. The message is processed and displayed
        publicly, allowing all players to see the interaction.

        Args:
            source_id (int): The ID of the player or system sending the message.
                            If 0, the message is from the system ("上帝").
            content (str): The content of the message to be sent publicly.
        """

        if source_id == 0:
            self.get_response(f"上帝：{content}",True)
        else:
            self.get_response(f"{source_id}号玩家：{content}",True)
        if add_to_context:
            Context(self.game,source_id,content,self.game.get_player(t="id",alive=False))

    def __str__(self):
        return f"玩家{self.id}（{self.role}）"

class Game:
    def __init__(self, game_name, players_info_path, apis_path, instructions_path):
        """
        Initialize a new game instance.

        Args:
            game_name (str): the name of the game
            players_info_path (str): the path to the players info json file
            apis_path (str): the path to the apis json file
            instructions_path (str): the path to the instructions json file

        Attributes:
            game_name (str): the name of the game
            instructions (dict): the instructions for the game
            apis (dict): the apis for the game
            players_info (dict): the players info for the game
            players (list): the players in the game
            id (int): the id of the game
            stage (int): the current stage of the game
            kill_tonight (list): the players to be killed tonight
        """
        self.game_name = game_name
        self.stage = 0
        self.id = time()
        self.set_logger()
        
        self.instructions = read_json(instructions_path)
        self.apis = read_json(apis_path)
        self.players_info = read_json(players_info_path)
        
        self.client = OpenAI(api_key = self.apis["Model abbreviation"]["api_key"], base_url = self.apis["Model abbreviation"]["base_url"])
        
        self.players = []
        self.init_game()
        self.kill_tonight = []

    def set_logger(self):
        """
        Set up the logger for the game.

        The logger will output logs to the console and a markdown file
        named `<game_name>.md` in the `log` directory.

        Args:
            game_name (str): The name of the game.

        Returns:
            None
        """
        
        logger = logging.getLogger(str(self.id))
        logger.setLevel(logging.DEBUG)

        # 创建控制台处理器 (Console Handler)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # 创建文件处理器 (File Handler)
        if not os.path.exists("./log"):
            os.mkdir("./log")
        log_file_path = f"./log/{self.game_name}-id={self.id}.md"
        fh = logging.FileHandler(log_file_path, encoding="UTF-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(
            '**%(asctime)s - %(levelname)s**\n%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))

        # 设置日志格式
        formatter = logging.Formatter('**%(asctime)s - %(levelname)s**\n%(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        # 将处理器添加到 logger
        logger.addHandler(ch)
        logger.addHandler(fh)

        # 初始化日志文件内容
        with open(log_file_path, "w", encoding="UTF-8") as f:
            f.write(f"# {self.game_name}\n\n")

        self.logger = logger

    def init_game(self):
        """
        Initializes the game by creating player instances and setting up the initial context.

        This function iterates over the players_info dictionary to create Player
        objects for each player, excluding the entry with key "0". It then initializes
        system prompts for each player and sets up the initial game context with a
        broadcast message containing the game description.

        The initial game context is created with visibility to all players.

        """

        for i in self.players_info.keys():
            if i == "0" or i == 0:
                continue
            roles = self.players_info[i]["role"]
            Player(roles,int(i),self)
        for i in self.players:
            i.init_system_prompt()
        Context(self,0,self.players_info["0"],self.get_players(t="id",alive=False))

    def get_players(self,t = "object",alive = True , role = "all"):
        """
        Retrieves a list of players based on specified criteria.

        Args:
            t (str): Determines the return type. If "object", returns player objects.
                    If "id", returns player ids. Defaults to "object".
            alive (bool): If True, only includes players who are alive.
                        If False, includes all players regardless of status. Defaults to True.
            role (str): Specifies the role of players to retrieve. If "all", retrieves players of all roles.
                        Otherwise, retrieves players with the specified role. Defaults to "all".

        Returns:
            list: A list of players or player ids based on the criteria specified by the arguments.
        """

        if role == "all":
            if alive:
                if t == "object":
                    return [i for i in self.players if i.alive]
                elif t == "id":
                    return [i.id for i in self.players if i.alive]
            else:
                if t == "object":
                    return self.players
                elif t == "id":
                    return [i.id for i in self.players]
        else:
            if alive:
                if t == "object":
                    return [i for i in self.players if i.role == role and i.alive]
                elif t == "id":
                    return [i.id for i in self.players if i.role == role and i.alive]
            else:
                if t == "object":
                    return [i for i in self.players if i.role == role]
                elif t == "id":
                    return [i.id for i in self.players if i.role == role]

    def get_players_by_ids(self,ids:list):
        """
        Returns a list of players according to given ids.

        Args:
            ids (list): A list of player ids.

        Returns:
            list: A list of players with the given ids.
        """
        ids = [int(i) for i in ids]
        players_pending = [i for i in self.players if i.id in ids]
        return players_pending

    def werewolf_killing(self):
        """
        Executes the werewolf killing phase during the night.

        This function handles the process where werewolf players decide which player
        to kill during the night. It sends a message to all werewolf players asking
        them to select a target for elimination. The players then vote on a target
        and the one with the most votes is marked for killing. If a player is
        successfully chosen to be killed, a context message is created to indicate
        the player's elimination. If no decision is reached, a failure message is
        logged.

        The function updates the `kill_tonight` list with the id of the player
        chosen to be killed.

        Returns:
            None
        """

        players_pending = self.get_players(role="werewolf")
        if not players_pending:
            return
        content = "今晚你想杀谁？"
        for i in players_pending:
            i.private_chat(0,content)
        content = "请进行杀人投票，杀人投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以自由发言解释杀人理由。"
        for i in players_pending:
            i.private_chat(0,content)
        result = {i.id:0 for i in self.get_players()}
        for i in players_pending:
            voted = extract_numbers_from_brackets(i.messages[-1]['content'])
            if voted and int(voted[-1]) in self.get_players("id"):
                result[int(voted[-1])] += 1
        killed = find_max_key(result)
        if killed:
            Context(self,0,f"今晚{killed}号玩家被杀了",self.get_players(t="id",role="werewolf",alive=False))
            self.kill_tonight.append(killed)
        else:
            Context(self,0,f"击杀失败",self.get_players(t="id",role="werewolf",alive=False))

    def seer_seeing(self):
        """
        Now it's the seer's turn to see someone's role.

        1. The seer is asked to input the id of the player they want to see.
        2. The seer is given the role of the player they want to see.

        The message flow is as follows:
        Server -> Seer: "你今晚要查谁？"
        Seer -> Server: "[7]号玩家"
        Server -> Seer: "你今晚要查的玩家是7号玩家，他的身份是witch"
        """
        seer = self.get_players(role="seer",alive=False)
        if not seer:
            return
        seer = seer[0]
        if not seer.alive:
            return
        seer.private_chat(0,"你今晚要查谁？要查询的玩家编号请用[]包围，例如'我要查询[7]号玩家'。可以简短的给出理由。")
        target = extract_numbers_from_brackets(seer.messages[-1]['content'])
        seer.private_chat(0,f"你今晚要查的玩家是{self.get_players_by_ids(target)[0]}，他的身份是{self.get_players_by_ids(target)[0].role}")

    def witch_operation(self):
        """
        女巫的操作
        如果今晚有人被杀，女巫可以选择救他或者不救
        如果女巫选择救他，女巫将被标记为抗毒
        如果女巫选择不救，女巫可以选择毒杀别人
        如果女巫选择毒杀，女巫将被标记为毒药
        如果女巫没有毒药，女巫不能毒杀
        """
        witch = self.get_players(role="witch",alive=False)
        if not witch:
            return
        witch = witch[0]
        if not witch.alive:
            return
        if self.kill_tonight:
            if not witch.poison and not witch.antidote:
                witch.private_chat(0,f"今晚{self.kill_tonight}号玩家被杀了，你可以选择救或者不救，选择结果用[]包围，例如要救{self.kill_tonight[0]}号玩家，请写[{self.kill_tonight[0]}]，不救请写[0]，你可以简短的给出理由。另外，你今晚还有毒药，如果不救，你可以选择毒杀别人，如果不救，是否毒杀将在下一条消息中选择，本次回复无需选择，只需要回答救或者不救这一问题。")
                voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                if voted and int(voted[-1]):
                    witch.antidote = True
                    Context(self,0,f"今晚{self.kill_tonight}号玩家被杀了，你选择了救{voted[-1]}号玩家",self.get_players(t="id",alive=False,role="witch"))
                    self.kill_tonight.remove(int(voted[-1]))
                else:
                    Context(self,0,f"今晚{self.kill_tonight}号玩家被杀了，你选择了不救他",self.get_players(t="id",alive=False,role="witch"))
                    witch.private_chat(0,f"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。")
                    voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                    if int(voted[-1]):
                        witch.poison = True
                        Context(self,0,f"今晚{self.kill_tonight}号玩家被杀了，你选择了毒杀{int(voted[-1])}号玩家",self.get_players(t="id",alive=False,role="witch"))
                        self.kill_tonight.append(int(voted[-1]))
                    else:
                        Context(self,0,f"今晚{self.kill_tonight}号玩家被杀了，你选择了不毒杀",self.get_players(t="id",alive=False,role="witch"))
            elif not witch.antidote and witch.poison:
                witch.private_chat(0,f"今晚{self.kill_tonight}号玩家被杀了，你可以选择救他或者不救，选择结果用[]包围，救请写[1]，不救请写[0]，你可以简短的给出理由。另外，你今晚没有毒药了。")
                voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                if voted and int(voted[-1]) == 1:
                    witch.antidote = True
                    Context(self,0,f"今晚{self.kill_tonight}号玩家被杀了，你选择了救他",self.get_players(t="id",alive=False,role="witch"))
                    self.kill_tonight.remove(int(voted[-1]))
            elif witch.antidote and not witch.poison:
                witch.private_chat(0,"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。")
                voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                if int(voted[-1]):
                    witch.poison = True
                    Context(self,0,f"你选择了毒杀{int(voted[-1])}号玩家",self.get_players(t="id",alive=False,role="witch"))
                    self.kill_tonight.append(int(voted[-1]))
                else:
                    Context(self,0,f"你选择了不毒杀",self.get_players(t="id",alive=False,role="witch"))
            else:
                pass
        else:
            if not witch.poison:
                witch.private_chat(0,"你可以选择毒杀别人，选择结果用[]包围，毒杀结果请写在[]中，例如你要杀1号玩家，请写[1]，不毒杀请写[0]。")
                voted = extract_numbers_from_brackets(witch.messages[-1]['content'])
                if int(voted[-1]):
                    witch.poison = True
                    Context(self,0,f"你选择了毒杀{int(voted[-1])}号玩家",self.get_players(t="id",alive=False,role="witch"))
                    self.get_players_by_ids([int(voted[-1])])[0].alive = False
                else:
                    Context(self,0,f"你选择了不毒杀",self.get_players(t="id",alive=False,role="witch"))
            else:
                pass

    def public_discussion(self):
        """
        Public discussion process. Sends a message to all players to discuss,
        then collects all the discussion content and shows it to all players.

        Returns:
            None
        """
        players_pending = self.get_players()
        content = "请公开讨论，在此阶段你可以简短发言，解释讨论理由。"
        Context(self,0,content,self.get_players(t="id",alive=False))
        for i in players_pending:
            i.pub_chat(0,content,add_to_context=False)

    def vote(self) -> dict:
        """
        Voting process. First, sends a message to all players to vote. Then,
        collects all the votes and returns a dictionary where the keys are the
        player ids and the values are the number of votes they got.

        Returns:
            dict: A dictionary where the keys are the player ids and the values
                are the number of votes they got.
        """
        players_pending = self.get_players()
        content = "请投票，投票结果用[]包围，其中只包含编号数字，例如[1]。在此阶段你可以简短发言，解释投票理由。"
        Context(self,0,content,self.get_players(t="id",alive=False))
        for i in players_pending:
            i.pub_chat(0,content,add_to_context=False)
        result = {i.id:0 for i in players_pending}
        for i in players_pending:
            voted = extract_numbers_from_brackets(i.messages[-1]['content'])
            if voted and int(voted[-1]) in self.get_players("id"):
                            result[int(voted[-1])] += 1
        return result

    def game_over(self) -> int:
        """
        Determines if the game is over and declares the winner.

        Checks the number of alive players and compares the number of werewolves to the
        number of non-werewolf players. If the number of werewolves is greater than or
        equal to the non-werewolf players, the werewolves win. If there are no remaining
        werewolves, the non-werewolf players win. Returns 1 if the game is over, otherwise 0.

        Returns:
            int: 1 if the game is over (either werewolves or non-werewolves have won),
            0 if the game is not yet over.
        """

        if len(self.get_players(alive=True)) - 2*len(self.get_players(alive=True,role="werewolf")) < 0: # 好人数量小于狼人数量
            return 1
        elif len(self.get_players(alive=True,role="werewolf")) == 0:
            return 1
        else:
            return 0

    def get_winner(self) -> str:
        if self.game_over():
            if len(self.get_players(alive=True)) - 2*len(self.get_players(alive=True,role="werewolf")) < 0:
                Context(self,0,f"游戏结束，狼人获胜",self.get_players(t="id",alive=False))
                return "狼人"
            elif len(self.get_players(alive=True,role="werewolf")) == 0:
                Context(self,0,f"游戏结束，好人获胜",self.get_players(t="id",alive=False))
                return "好人"

    def private_chat(self,player_id:int,content:str):
        """
        Allows a player to send a private chat message to the game.

        Args:
            player_id (int): The ID of the player sending the message.
            content (str): The content of the chat message to be sent.
        """
        self.get_players_by_ids([player_id])[0].private_chat(0,content)

    def public_chat(self,player_id:int,content:str,add_to_context:bool=True):
        """
        Allows a player to send a public chat message.

        Args:
            player_id (int): The ID of the player sending the message.
            content (str): The content of the chat message to be sent.
        """

        self.get_players_by_ids([player_id])[0].pub_chat(0,content,add_to_context)

    def broadcast(self,content):
        """
        Broadcast a message to all players.

        Args:
            content (str): content of the message to be broadcasted
        """
        Context(self,0,content,self.get_players(t="id",alive=False))

    def out(self,player_ids:list):
        """
        to out players, given player_ids list.
        this will directly set the alive status of given players to False,
        and broadcast the message to all players.

        Args:
            player_ids (list): list of player ids
        """
        if not player_ids:
            self.broadcast("出局失败")
            return
        players_pending = self.get_players_by_ids(player_ids)
        if not players_pending:
            raise ValueError("出局失败")
        for i in players_pending:
            i.alive = False
        self.broadcast(f"{str(player_ids)[1:-1]}号玩家出局")

    def no_out(self,player_ids:list):
        """
        to no out players, given player_ids list.
        this will directly set the alive status of given players to True,
        and broadcast the message to all players.
        Args:
            player_ids (list): list of player ids
        """
        if not player_ids:
            self.broadcast("加入失败")
            return
        players_pending = self.get_players_by_ids(player_ids)
        if not players_pending:
            raise ValueError("加入失败")
        for i in players_pending:
            i.alive = True
        self.broadcast(f"{str(player_ids)[1:-1]}号玩家加入")

    def day_night_change(self):
        """
        Advances the game stage by one, transitioning between day and night.

        This function increments the game stage, determines the current day and time (day or night),
        and broadcasts the current game stage to all players. If it is morning of any day after the first,
        it checks if any players were marked to be killed overnight. If there are, it broadcasts the list
        of players who were killed and updates their status. If no players were marked for death,
        it announces that no deaths occurred overnight.
        """

        self.stage += 1
        days,morning_dusk = self.get_game_stage()
        self.broadcast(f"现在是第{days}天{'白天' if morning_dusk else '晚上'}")
        if morning_dusk == 1 and days > 1:
            if self.kill_tonight:
                self.kill_tonight = list(set(self.kill_tonight))
                self.broadcast(f"昨晚{str(self.kill_tonight)[1:-1]}号玩家被杀了")
                self.out(self.kill_tonight)
                self.kill_tonight = []
            else:
                self.broadcast(f"昨晚是个平安夜，没有人被杀")

    def get_game_stage(self):
        """
        Returns the current game stage as a tuple of two integers.

        The first element of the tuple is the current day number (1-indexed),
        and the second element is 1 if the current time is day, and 0 if it
        is night.

        The game stage starts at 0, and increments by 1 each time the
        day_night_change method is called. The current day number is the
        integer division of the game stage by 2, plus 1. The current time
        (day or night) is determined by the remainder of the game stage
        divided by 2.

        Returns:
            tuple: A tuple of two integers, (days, morning_dusk),
                where days is the current day number (1-indexed), and
                morning_dusk is 1 if the current time is day, and 0 if
                it is night.
        """
        days = self.stage//2 + 1
        morning_dusk = (self.stage + 1) % 2 # 1表示白天，0表示晚上
        return days,morning_dusk

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return f"{self.game_name}：第{self.get_game_stage()[0]}天{'白天' if self.get_game_stage()[1] else '晚上'}"

    def __eq__(self, value):
        return self.id == value.id


if __name__ == "__main__":
    # 输入路径配置
    # 控制台运行程序
    instructions_path = "./config/instructions.json"
    apis_path = "./config/api_template.json"
    players_info_path = "./config/player_info.json"
    game_name = input("请输入游戏名称：")
    mode = input("请输入游戏模式（1、全自动模式，2、手动模式）：")

    game = Game(game_name, players_info_path, apis_path, instructions_path)
    
    if mode == "2":
        # 增加手动控制游戏逻辑
        # 手动控制游戏进程
        
        while True:
            print("\n————————————————————")
            print("游戏开始! 输入命令控制游戏进程:")
            print("1: 进入下一夜")
            print("2: 狼人杀人阶段") 
            print("3: 预言家查验阶段")
            print("4: 女巫操作阶段")
            print("5: 公共讨论阶段")
            print("6: 投票阶段")
            print("7: 查看当前游戏状态")
            print("8: 结束游戏")
            print("————————————————————")
            cmd = input("\n请输入命令(1-8): ")
            
            if cmd == "1":
                # 进入下一夜
                game.day_night_change()
                print(f"已进入: 第{game.get_game_stage()[0]}天{'白天' if game.get_game_stage()[1] else '晚上'}")
            elif cmd == "2":
                # 狼人杀人
                game.werewolf_killing()
                print("狼人杀人阶段结束")
            elif cmd == "3":
                # 预言家查验
                game.seer_seeing()
                print("预言家查验阶段结束") 
            elif cmd == "4":
                # 女巫操作
                game.witch_operation()
                print("女巫操作阶段结束")
            elif cmd == "5":
                game.day_night_change()
                print(f"已进入: 第{game.get_game_stage()[0]}天{'白天' if game.get_game_stage()[1] else '晚上'}")
                # 公共讨论
                game.public_discussion()
                print("公共讨论阶段结束")
            elif cmd == "6":
                # 投票
                result = find_max_key(game.vote())
                game.out([result])
                print("投票阶段结束")
            elif cmd == "7":
                # 显示当前状态
                print(f"\n当前游戏状态:")
                print(f"游戏名称: {game.game_name}")
                print(f"游戏阶段: 第{game.get_game_stage()[0]}天{'白天' if game.get_game_stage()[1] else '晚上'}")
                print("\n存活玩家:")
                for player in game.get_players(alive=True):
                    print(f"玩家{player.id}({player.role})")
            elif cmd == "8":
                # 结束游戏
                print("游戏已手动结束")
                exit(0)
            else:
                print("无效的命令,请重新输入")
                
            # 检查游戏是否结束
            if game.game_over():
                game.get_winner()
                break
    elif mode == "1":
        # 全自动模式
        print("\n游戏开始! 自动控制游戏进程:")
        while not game.game_over():
            game.day_night_change()
            game.werewolf_killing()
            game.seer_seeing()
            game.witch_operation()
            game.day_night_change()
            if game.game_over():
                game.get_winner()
                break
            game.public_discussion()
            result = find_max_key(game.vote())
            game.out([result])
    else:
        print("无效的命令，进程自动退出...")