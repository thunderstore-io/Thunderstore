from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from thunderstore.community.models import PackageListing
from thunderstore.repository.models import Comment


def clean_content(content: str) -> str:
    return content.strip()


class CreateCommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]

    def __init__(
        self,
        user: User,
        parent_object: PackageListing,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.parent_object = parent_object

    def clean_content(self) -> str:
        return clean_content(self.cleaned_data["content"])

    def save(self, *args, **kwargs) -> Comment:
        self.instance.author = self.user
        self.instance.parent_object = self.parent_object
        return super().save(*args, **kwargs)


class EditCommentForm(forms.Form):
    content = forms.CharField(max_length=Comment._meta.get_field("content").max_length)
    is_pinned = forms.BooleanField(required=False)

    def __init__(self, user: User, comment: Comment, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.comment = comment

    def can_edit_content(self) -> bool:
        # Only the comment author can edit a comment's content
        return self.user == self.comment.author

    def can_pin(self) -> bool:
        parent_object = self.comment.parent_object
        if isinstance(parent_object, PackageListing):
            # Must be a member of the identity to pin
            return parent_object.package.owner.members.filter(user=self.user).exists()
        raise NotImplementedError()

    def clean_content(self) -> str:
        content = clean_content(self.cleaned_data["content"])

        if content != self.comment.content and not self.can_edit_content():
            raise ValidationError("Cannot edit content")

        return content

    def clean_is_pinned(self) -> bool:
        is_pinned = self.cleaned_data.get("is_pinned")

        if is_pinned != self.comment.is_pinned and not self.can_pin():
            raise ValidationError("Cannot edit pinned status")

        return is_pinned

    def save(self) -> Comment:
        self.comment.content = self.cleaned_data.get("content")
        self.comment.is_pinned = self.cleaned_data.get("is_pinned")
        self.comment.save(update_fields=("content", "is_pinned"))
        return self.comment
