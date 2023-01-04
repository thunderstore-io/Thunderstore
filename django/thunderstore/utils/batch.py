from typing import Iterable, List, TypeVar

T = TypeVar("T")


def batch(batch_size: int, iterable: Iterable[T]) -> Iterable[List[T]]:
    collected = []
    for entry in iterable:
        collected.append(entry)
        if len(collected) >= batch_size:
            yield collected
            collected = []
    if len(collected) > 0:
        yield collected
