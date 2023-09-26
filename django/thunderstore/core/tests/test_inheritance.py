from thunderstore.core.enums import OptionalBoolChoice
from thunderstore.core.inheritance import get_effective_bool_choice_depth_first


def test_get_effective_bool_choice_depth_first():
    assert (
        get_effective_bool_choice_depth_first(
            OptionalBoolChoice.NONE,
            OptionalBoolChoice.NONE,
        )
        == OptionalBoolChoice.NONE
    )
    assert (
        get_effective_bool_choice_depth_first(
            OptionalBoolChoice.NO,
            OptionalBoolChoice.NONE,
            OptionalBoolChoice.YES,
        )
        == OptionalBoolChoice.YES
    )
    assert (
        get_effective_bool_choice_depth_first(
            OptionalBoolChoice.NO,
            OptionalBoolChoice.NONE,
            OptionalBoolChoice.NONE,
        )
        == OptionalBoolChoice.NO
    )
