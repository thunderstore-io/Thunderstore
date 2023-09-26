from thunderstore.core.enums import OptionalBoolChoice


def get_effective_bool_choice_depth_first(
    *args: OptionalBoolChoice,
) -> OptionalBoolChoice:
    for arg in reversed(args):
        if arg != OptionalBoolChoice.NONE:
            return arg
    return OptionalBoolChoice.NONE
