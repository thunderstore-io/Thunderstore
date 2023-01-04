import pytest
from django.db.models import Q

from thunderstore.repository.package_formats import PackageFormats

"""
This test file should always be up to date on all the currently and previously
supported package formats.

NO FORMATS SHOULD BE REMOVED FROM TRACKED_FORMATS EVEN IF NO LONGER SUPPORTED!

The formats will exist in the broader ecosystem regardless of what happens to
this project and as such they are also permanent.

The TRACKED_FORMATS copy here exists in order to catch ill-informed
modifications to the original set, such as deletions, which would otherwise
be impossible to do.
"""

TRACKED_FORMATS = [
    "thunderstore.io:v0.0",
    "thunderstore.io:v0.1",
    "thunderstore.io:v0.2",
]


def test_package_formats_tracked_in_test():
    """
    If this fails and you've added new entries to PackageFormats, add the new
    entries to TRACKED_FORMATS above. If you have deleted entries from
    PackageFormats, do nothing and reconsider the change, as it is generally
    not a valid action to delete entries from PackageFormats.
    """
    if set(TRACKED_FORMATS) != set(PackageFormats.values):
        raise Exception("TRACKED_FORMATS is out of date")


def test_package_formats_no_deletions():
    """
    If this fails, DO NOT modify TRACKED_FORMATS, but instead add the value
    you removed from PackageFormats back to it.
    """
    if not all([x in PackageFormats.values for x in TRACKED_FORMATS]):
        raise Exception(
            "PackageFormats has been incorrectly modified, deletions aren't allowed."
        )


@pytest.mark.parametrize("allow_none", (False, True))
@pytest.mark.parametrize("field_name", ("test", "lol"))
def test_package_formats_as_query_filter(field_name: str, allow_none: bool):
    result = PackageFormats.as_query_filter("field_name", allow_none=allow_none)
    expected = [("field_name", x) for x in PackageFormats.values]
    if allow_none:
        expected += [("field_name", None)]
    assert result.connector == Q.OR
    assert len(result.children) == len(expected)
    assert set(expected) == set(result.children)
