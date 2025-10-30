def format_datetime(date_or_string):
    if date_or_string is None:
        return None
    if isinstance(date_or_string, str):
        return date_or_string
    try:
        return date_or_string.isoformat()
    except AttributeError:
        return None
