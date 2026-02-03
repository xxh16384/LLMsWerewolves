# core/io.py


class IOInterface:

    def CLI_output(
        self, content: str, source: str = "System", if_show_source: bool = False
    ):
        if if_show_source:
            print(f"[{source}] {content}")
        else:
            print(f"{content}")

    def CLI_input(
        self, prompt: str, source: str = "System", if_show_source: bool = False
    ) -> str:
        if if_show_source:
            return input(f"[{source}] {prompt}")
        else:
            return input(f"{prompt}")

    def CLI_s_output(
        self,
        content: str,
        source: str = "System",
        if_first: bool = False,
        if_show_source: bool = False,
    ):
        if if_first and if_show_source:
            print(f"[{source}] {content}", end="", flush=True)
        else:
            print(f"{content}", end="", flush=True)


cur_io = IOInterface()
