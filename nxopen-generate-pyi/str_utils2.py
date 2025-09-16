
import typing


WHITESPACE = [" ", "\r", "\n", "\t"]
QUOTES = ["'", "\""]


def parse_with_callbacks(
        text: 'str|typing.Collection[str]',
        handlers: 'list[typing.Callable[[list[str], str, int], None]]',
        start_i: int = 0,
        end_i: int = -1,
        ) -> None:
    if isinstance(text, str):
        letters: list[str] = list(text)
    else:
        letters: list[str] = text  # type: ignore

    i = start_i
    if end_i == -1:
        end_i = len(letters)
    while i < end_i:
        for h in handlers:
            h(letters, letters[i], i)
        i += 1


