def get_nested_value(data, path: str, default=None):
    """从嵌套字典/列表中按点号路径取值。

    示例:
        get_nested_value({"a": {"b": [1, 2, 3]}}, "a.b[1]")  -> 2
        get_nested_value({"a": {"b": {"c": "x"}}}, "a.b.c") -> "x"
    """
    if data is None:
        return default

    keys = []
    current = ""
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if current:
                keys.append(current)
                current = ""
        elif ch == "[":
            if current:
                keys.append(current)
                current = ""
            j = path.find("]", i)
            if j == -1:
                raise ValueError(f"路径格式错误，缺少闭合括号: {path}")
            keys.append(int(path[i + 1:j]))
            i = j
        else:
            current += ch
        i += 1

    if current:
        keys.append(current)

    try:
        for key in keys:
            if isinstance(data, dict):
                data = data[key]
            elif isinstance(data, list):
                data = data[key]
            else:
                return default
        return data
    except (KeyError, IndexError, TypeError):
        return default
