from collections.abc import Iterable, Iterator
from typing import Any


def flatten(items: Any) -> Iterator[Any]:
    if isinstance(items, Iterable) and not isinstance(items, (str, bytes)):
        for item in items:
            yield from flatten(item)
    else:
        yield items
