from typing import List, TypeVar, Tuple, Iterable

T = TypeVar("T")


def pairs(lst: List[T], circular=False) -> Iterable[Tuple[T, T]]:
    """
    Loop through all pairs of successive items in a list.

    >>> list(pairs([1, 2, 3, 4]))
    [(1, 2), (2, 3), (3, 4)]
    >>> list(pairs([1, 2, 3, 4], circular=True))
    [(1, 2), (2, 3), (3, 4), (4, 1)]
    """
    i = iter(lst)
    first = prev = item = next(i)
    for item in i:
        yield prev, item
        prev = item
    if circular:
        yield item, first