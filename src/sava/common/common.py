from typing import Iterable


def flatten(items):
    if isinstance(items, Iterable) and not isinstance(items, (str, bytes)):
        for item in items:
            yield from flatten(item)
    else:
        yield items
