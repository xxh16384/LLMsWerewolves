# core/io.py


from abc import ABC, abstractmethod


# 到时候在这里做一些别的input和output接口，用不同的类，然后让IOInterface继承不同的类来实现一键切换


class IOInterface(ABC):

    @staticmethod
    @abstractmethod
    def IO_output(
        content: str, source: str = "System", if_show_source: bool = False
    ) -> None:
        pass

    @staticmethod
    @abstractmethod
    def IO_input(
        prompt: str, source: str = "System", if_show_source: bool = False
    ) -> str:
        pass

    @staticmethod
    @abstractmethod
    def IO_s_output(
        content: str,
        source: str = "System",
        if_first: bool = False,
        if_show_source: bool = False,
    ) -> None:
        pass


class CLI_IO(IOInterface):

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


class WEB_IO(IOInterface):

    @staticmethod
    def IO_output(
        content: str, source: str = "System", if_show_source: bool = False
    ) -> None:
        pass

    @staticmethod
    def IO_input(
        prompt: str, source: str = "System", if_show_source: bool = False
    ) -> str:
        pass

    @staticmethod
    def IO_s_output(
        content: str,
        source: str = "System",
        if_first: bool = False,
        if_show_source: bool = False,
    ) -> None:
        pass


# cur_io = WEB_IO()

# 现在使用命令端方式的IO
cur_io = CLI_IO()
