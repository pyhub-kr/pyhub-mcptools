from pyhub.mcptools.core.q2 import q_task, TaskGroup


@q_task(group=TaskGroup.XLWINGS)
def add(x: int, y: int) -> int:
    return x + y
