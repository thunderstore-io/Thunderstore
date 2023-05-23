from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from thunderstore.account.factories import UserFlagFactory, UserFlagMembershipFactory
from thunderstore.account.models import UserFlag
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType


@pytest.mark.django_db
def test_user_flags_empty_for_unauthenticated(
    user_flag: UserFlag,
):
    start_time = timezone.now()
    late_time = timezone.now() + timedelta(days=10)

    UserFlagMembershipFactory(
        flag=user_flag,
        datetime_valid_from=start_time,
        datetime_valid_until=None,
    )

    assert UserFlag.get_active_flags_on_user(None, late_time) == []
    assert UserFlag.get_active_flags_on_user(AnonymousUser(), late_time) == []


@pytest.mark.django_db
def test_user_flags_overlapping_memberships_return_distinct(
    user: UserType,
    user_flag: UserFlag,
):
    early_time = timezone.now()
    start_time = early_time + timedelta(seconds=1)
    late_time = start_time + timedelta(days=100000)

    for _ in range(3):
        UserFlagMembershipFactory(
            user=user,
            flag=user_flag,
            datetime_valid_from=start_time,
            datetime_valid_until=None,
        )

    assert UserFlag.get_active_flags_on_user(user, early_time) == []
    assert UserFlag.get_active_flags_on_user(user, late_time) == [user_flag.identifier]
    assert UserFlag.get_active_flags_on_user(None, late_time) == []


@pytest.mark.django_db
def test_user_flags_without_end_time_are_active(
    user: UserType,
    user_flag: UserFlag,
):
    early_time = timezone.now()
    start_time = early_time + timedelta(seconds=1)
    late_time = start_time + timedelta(days=100000)

    UserFlagMembershipFactory(
        user=user,
        flag=user_flag,
        datetime_valid_from=start_time,
        datetime_valid_until=None,
    )
    assert UserFlag.get_active_flags_on_user(user, early_time) == []
    assert UserFlag.get_active_flags_on_user(user, late_time) == [user_flag.identifier]
    assert UserFlag.get_active_flags_on_user(None, late_time) == []


@pytest.mark.django_db
def test_user_flags_past_end_time_are_inactive(
    user: UserType,
    user_flag: UserFlag,
):
    early_time = timezone.now()
    start_time = early_time + timedelta(days=1)
    middle_time = start_time + timedelta(days=1)
    almost_end_time = middle_time + timedelta(days=1)
    end_time = almost_end_time + timedelta(microseconds=1)
    late_time = end_time + timedelta(days=1)

    UserFlagMembershipFactory(
        user=user,
        flag=user_flag,
        datetime_valid_from=start_time,
        datetime_valid_until=end_time,
    )

    assert UserFlag.get_active_flags_on_user(user, early_time) == []
    assert UserFlag.get_active_flags_on_user(user, start_time) == [user_flag.identifier]
    assert UserFlag.get_active_flags_on_user(user, middle_time) == [
        user_flag.identifier
    ]
    assert UserFlag.get_active_flags_on_user(None, middle_time) == []
    assert UserFlag.get_active_flags_on_user(user, almost_end_time) == [
        user_flag.identifier
    ]
    assert UserFlag.get_active_flags_on_user(user, end_time) == []
    assert UserFlag.get_active_flags_on_user(user, late_time) == []


@pytest.mark.django_db
def test_user_flags_multiple_users_and_flags():
    user1, user2 = [UserFactory() for _ in range(2)]
    flag1, flag2, flag3 = [UserFlagFactory() for _ in range(3)]

    early_time = timezone.now()
    start_time = early_time + timedelta(days=1)
    check_time = start_time + timedelta(days=1)
    late_time = check_time + timedelta(days=1)

    # User 1:
    # - expired flag1 membership
    # - active flag2 membership
    # - no flag3 membership
    UserFlagMembershipFactory(
        user=user1,
        flag=flag1,
        datetime_valid_from=early_time,
        datetime_valid_until=start_time,
    )
    UserFlagMembershipFactory(
        user=user1,
        flag=flag2,
        datetime_valid_from=early_time,
        datetime_valid_until=late_time,
    )

    # User 2:
    # - upcoming flag1 membership
    # - active flag2 membership
    # - infinitely active flag3 membership
    UserFlagMembershipFactory(
        user=user2,
        flag=flag1,
        datetime_valid_from=late_time,
        datetime_valid_until=None,
    )
    UserFlagMembershipFactory(
        user=user2,
        flag=flag2,
        datetime_valid_from=early_time,
        datetime_valid_until=late_time,
    )
    UserFlagMembershipFactory(
        user=user2,
        flag=flag3,
        datetime_valid_from=early_time,
        datetime_valid_until=None,
    )

    assert UserFlag.get_active_flags_on_user(user1, check_time) == [
        flag2.identifier,
    ]
    assert UserFlag.get_active_flags_on_user(user2, check_time) == [
        flag2.identifier,
        flag3.identifier,
    ]


@pytest.mark.django_db
def test_user_flag_str():
    flag = UserFlagFactory(name="Name", app_label="test")
    assert str(flag) == f"test: Name"
