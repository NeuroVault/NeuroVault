def strip(value):
    if not value:
        return value
    return value.strip()


def logical_xor(a, b):
    return bool(a) ^ bool(b)
