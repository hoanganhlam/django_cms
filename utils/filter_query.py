def query_boolean(val, default=None):
    if val == 'true':
        return True
    elif val == "false":
        return False
    return default
