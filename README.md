# 大模型狼人杀！！

尝试做一个不同各种大语言模型狼人杀的小软件

## 本意

就是电子斗蛐蛐！！想以此来评价各家模型的优劣😋

## 使用

### api配置

配置api即可…？

api配置模板如下，主键是模型简称，用于程序调用
```json
{
    "Model abbreviation":{
        "api_key":"",
        "base_url":"",
        "model_name":""
    },
    "Model 2":{
        "api_key":"",
        "base_url":"",
        "model_name":""
    }
}
```

玩家配置详见player_info.json，可以为不同玩家指定不同的模型和角色。玩家的id应该是唯一的数字，否则可能报错哦。

记得配置游戏说明，也就是player_info.json中"0"对应的值。

### 基础指令

srds有webui了谁还用这些。。现在是全自动狼人杀时代
**过时的**

    + **b**：broadcast，上帝广播信息。
    + **exit**：退出程序。
    + **pr**：private chat，和某名玩家私聊。和狼人的私聊可以被全体狼人看到，和其它玩家的私聊只能被该玩家看到
    + **pu**：public chat，公共聊天，聊天内容可以被所有人看到。
    + **pu_batch**：批量公共聊天，一般用于白天的按顺序交流。
    <br>输入群发玩家编号：按顺序和玩家公共聊天，用英文逗号分隔，如“1,2,3”。可以不输入而**直接回车**，默认与所有存活的玩家按顺序公共聊天。
    + **vote**：投票，在投票结束后显示投票结果
    <br>请输入投票玩家编号：用法同上，**直接回车**可以让所有存活玩家投票
    + **out**：输入出局玩家编号，输入方法同上，没有快捷方法。在夜晚有人被杀或白天有人被投票出局时动用此方法。
    + **print_context**：调试用，输出所有上下文及其对应可视玩家id
    + **wolf_discuss**：狼队私聊讨论，暂时未完工。

### 扩展功能

可以在instruction.json中添加职业提示词实现更丰富的玩法，也可以修改general提示词以及vote()函数实现警徽玩法。

### 试试webui能不能用？

控制台运行

```bash
streamlit run webui.py
```

或者使用`启动webui.bat`启动webui

---

## 总之

这个小程序现在很粗糙，以后再完善吧）
