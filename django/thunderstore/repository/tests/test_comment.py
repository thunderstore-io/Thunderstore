import pytest

from thunderstore.core.factories import UserFactory
from thunderstore.repository.comment import (
    CreateCommentForm,
    EditCommentForm,
    clean_content,
)
from thunderstore.repository.models import (
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
)


def test_comment_clean_content():
    content = " Test content "
    assert "Test content" == clean_content(content)


@pytest.mark.django_db
def test_create_comment(user, active_package_listing):
    content = " Test content "
    form = CreateCommentForm(
        user,
        active_package_listing,
        data={"content": content, "is_pinned": False},
    )
    assert form.is_valid()
    comment = form.save()
    assert comment.content == clean_content(content)
    assert comment.author == user
    assert comment.is_pinned is False
    assert comment.thread == active_package_listing


@pytest.mark.django_db
def test_create_comment_too_long(user, active_package_listing):
    content = "x" * 10000
    form = CreateCommentForm(
        user,
        active_package_listing,
        data={"content": content, "is_pinned": False},
    )
    assert form.is_valid() is False
    assert len(form.errors["content"]) == 1
    assert (
        form.errors["content"][0]
        == "Ensure this value has at most 2048 characters (it has 10000)."
    )


@pytest.mark.django_db
def test_edit_comment(comment):
    new_content = " Edited content "
    form = EditCommentForm(
        user=comment.author,
        comment=comment,
        data={"content": new_content, "is_pinned": False},
    )
    assert form.is_valid()
    comment = form.save()
    assert comment.content == clean_content(new_content)
    assert comment.is_pinned is False


@pytest.mark.django_db
def test_edit_comment_too_long(comment):
    new_content = "x" * 10000
    form = EditCommentForm(
        user=comment.author,
        comment=comment,
        data={"content": new_content, "is_pinned": False},
    )
    assert form.is_valid() is False
    assert len(form.errors["content"]) == 1
    assert (
        form.errors["content"][0]
        == "Ensure this value has at most 2048 characters (it has 10000)."
    )


@pytest.mark.django_db
def test_edit_comment_not_allowed(comment):
    user = UserFactory.create()
    assert user != comment.author

    new_content = "Edited content"
    form = EditCommentForm(
        user=user,
        comment=comment,
        data={"content": new_content, "is_pinned": False},
    )
    assert form.is_valid() is False
    assert len(form.errors["content"]) == 1
    assert form.errors["content"][0] == "Cannot edit content"


@pytest.mark.django_db
def test_edit_comment_pin(comment):
    assert comment.is_pinned is False

    UploaderIdentityMember.objects.create(
        user=comment.author,
        identity=comment.thread.package.owner,
        role=UploaderIdentityMemberRole.owner,
    )

    form = EditCommentForm(
        user=comment.author,
        comment=comment,
        data={"content": comment.content, "is_pinned": True},
    )
    assert form.is_valid()
    comment = form.save()
    assert comment.is_pinned is True


@pytest.mark.django_db
def test_edit_comment_pin_not_allowed(comment):
    assert comment.is_pinned is False
    assert (
        comment.thread.package.owner.members.filter(
            user=comment.author,
        ).exists()
        is False
    )

    form = EditCommentForm(
        user=comment.author,
        comment=comment,
        data={"content": comment.content, "is_pinned": True},
    )
    assert form.is_valid() is False
    assert len(form.errors["is_pinned"]) == 1
    assert form.errors["is_pinned"][0] == "Cannot edit pinned status"
