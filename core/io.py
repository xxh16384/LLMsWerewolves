# core/io.py

# 到时候在这里做一些别的input和output接口，用不同的类，然后让IOInterface继承不同的类来实现一键切换


class CLI_IO:

    @staticmethod
    def IO_output(
        content: str, source: str = "System", if_show_source: bool = False
    ) -> None:
        if if_show_source:
            print(f"[{source}] {content}")
        else:
            print(f"{content}")

    @staticmethod
    def IO_input(
        prompt: str, source: str = "System", if_show_source: bool = False
    ) -> str:
        if if_show_source:
            return input(f"[{source}] {prompt}")
        else:
            return input(f"{prompt}")

    @staticmethod
    def IO_s_output(
        content: str,
        source: str = "System",
        if_first: bool = False,
        if_show_source: bool = False,
    ) -> None:
        if if_first and if_show_source:
            print(f"[{source}] {content}", end="", flush=True)
        else:
            print(f"{content}", end="", flush=True)


class IOInterface(CLI_IO):
    pass


cur_io = IOInterface()
