from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from thunderstore.community.models import Community
from thunderstore.repository.models import Comment, Package


def clean_content(content: str) -> str:
    return content.strip()


class CreateCommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]

    def __init__(
        self, user: User, package: Package, community: Community, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.package = package
        self.community = community

    def clean_content(self) -> str:
        return clean_content(self.cleaned_data["content"])

    def save(self, *args, **kwargs) -> Comment:
        self.instance.author = self.user
        self.instance.package = self.package
        self.instance.community = self.community
        return super().save(*args, **kwargs)


class EditCommentForm(forms.Form):
    content = forms.CharField(max_length=Comment._meta.get_field("content").max_length)
    pinned = forms.BooleanField()

    def __init__(self, user: User, comment: Comment, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.comment = comment

    def can_edit_content(self) -> bool:
        # Only the comment author can edit a comment's content
        return self.user == self.comment.author

    def can_pin(self) -> bool:
        # Must be a member of the identity to pin
        return self.comment.package.owner.members.filter(user=self.user).exists()

    def clean_content(self) -> str:
        return clean_content(self.cleaned_data["content"])

    def save(self, *args, **kwargs) -> Comment:
        content = self.cleaned_data.get("content")
        is_pinned = self.cleaned_data.get("is_pinned")

        if content != self.comment.content and not self.can_edit_content():
            raise ValidationError("Cannot edit content")

        if is_pinned != self.comment.is_pinned and not self.can_pin():
            raise ValidationError("Cannot edit pinned status")

        self.comment.content = content
        self.comment.is_pinned = is_pinned
        self.comment.save(update_fields=("content", "is_pinned"))
        return self.comment
