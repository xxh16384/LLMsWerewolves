from time import sleep
from .context import Context



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