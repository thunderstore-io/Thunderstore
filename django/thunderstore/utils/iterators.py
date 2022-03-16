from typing import Iterable, Iterator, TypeVar, Union

T = TypeVar("T", bound=Union[Iterable, Iterator])


def print_progress(iterator: T, max: int, frequency: int = 100) -> T:
    i = 0
    for i, result in enumerate(iterator):
        if i % frequency == 0:
            print(f"{i + 1} / {max}...")
        yield result
    print(f"{i + 1} / {max}")
