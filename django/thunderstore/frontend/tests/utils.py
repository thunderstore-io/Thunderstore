def get_url_kwarg(arg_name: str) -> str:
    # This would be petter if the params could be chosen based on the URL
    # pattern name, so consider exposing it here if more complex use cases
    # appear.
    return "32" if arg_name == "page" else "test"
