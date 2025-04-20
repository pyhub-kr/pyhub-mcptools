from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def applescript_list(value):
    """
    Convert a Python list to an AppleScript list format.

    Example:
    ["a", "b", "c"] -> {"a", "b", "c"}
    [1, 2, 3] -> {1, 2, 3}
    """
    if not value:
        return "{}"

    items = []
    for item in value:
        if isinstance(item, str):
            items.append(f'"{item}"')
        else:
            items.append(str(item))

    return mark_safe("{" + ", ".join(items) + "}")
