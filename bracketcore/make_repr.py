from typing import Callable, Union, Any


def make_repr(func: Callable, *items: list[tuple | tuple[Any, str]], fail_value: Any = ...) -> str:
    """
    Creates a pretty repr for a given class's `__init__` function (although any function can technically be used).
    ```
    class ExampleClass:
        def __init__(self, a, b, *, c = None) -> None:
            self._repr = make_repr(
                ExampleClass.__init__,
                (a,),
                (b,),
                (c, "c"), # Any keyword arguments should have the name of the keyword argument as the second value in the tuple
                fail_value = None
            )
            ...
        

        def __repr__(self) -> str:
            return self._repr
    

    inst = ExampleClass("value_for_a", "value_for_b")
    print(inst)
    >>> ExampleClass.__init__("value_for_a", "value_for_b")


    inst = ExampleClass("value_for_a", "value_for_b", c = "value_for_c")
    print(inst)
    >>> ExampleClass.__init__("value_for_a", "value_for_b", c = "value_for_c")

    ```
    """
    def dump_if_str(item) -> str:
        return f"\"{str(item)}\"" if isinstance(item, str) else str(item)
    posargs : list[tuple[Any]]      = list(filter(lambda x: len(x) == 1, items))
    kwargs  : list[tuple[Any, str]] = list(filter(lambda x: len(x) == 2 and x[0] != fail_value, items))
    args    : list[str]             = []
    args.extend([dump_if_str(posarg[0]) for posarg in posargs])
    args.extend([kwarg[1] + "=" + dump_if_str(kwarg[0]) for kwarg in kwargs])
    return func.__qualname__ + "(" + ", ".join(args) + ")"