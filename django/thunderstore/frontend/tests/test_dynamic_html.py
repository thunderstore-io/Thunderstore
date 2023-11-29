from typing import List

import pytest

from thunderstore.account.factories import UserFlagFactory
from thunderstore.frontend.models import DynamicHTML, DynamicPlacement


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("required_flags", "excluded_flags", "user_flags", "should_match"),
    (
        ([], [], [], True),
        ([], [], ["flag-1"], True),
        (["flag-1"], [], [], False),
        (["flag-1"], [], ["flag-1"], True),
        (["flag-1"], [], ["flag-1", "flag-2"], True),
        ([], ["flag-2"], [], True),
        ([], ["flag-2"], ["flag-2"], False),
        ([], ["flag-2"], ["flag-1", "flag-2"], False),
        (["flag-1"], ["flag-2"], ["flag-1"], True),
        (["flag-1"], ["flag-1", "flag-2"], ["flag-1"], False),
        (["flag-1", "flag-2"], [], ["flag-2"], True),
    ),
)
def test_dynamic_html_user_flag_filtering(
    required_flags: List[str],
    excluded_flags: List[str],
    user_flags: List[str],
    should_match: bool,
):
    flag_ids = set().union((*required_flags, *excluded_flags))
    flags = {}

    for flag_id in flag_ids:
        flags[flag_id] = UserFlagFactory(identifier=flag_id)

    placement = DynamicPlacement.content_beginning
    dhtml = DynamicHTML.objects.create(
        name="Test HTML",
        placement=placement,
    )
    dhtml.exclude_user_flags.set([flags[x] for x in excluded_flags])
    dhtml.require_user_flags.set([flags[x] for x in required_flags])

    matches = DynamicHTML.get_for_community(None, placement, user_flags)
    if should_match:
        assert matches.count() == 1
        assert matches.first() == dhtml
    else:
        assert matches.count() == 0
