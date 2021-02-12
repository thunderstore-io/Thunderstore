from django import forms
from django.contrib.auth.models import User

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
        commented_object: PackageListing,
        *args,
        **kwargs,
    ) -> None:
        if not isinstance(commented_object, PackageListing):
            raise ValueError("Unsupported parent object for comment")

        super().__init__(*args, **kwargs)
        self.user = user
        self.commented_object = commented_object

    def clean_content(self) -> str:
        return clean_content(self.cleaned_data["content"])

    def save(self, *args, **kwargs) -> Comment:
        self.instance.author = self.user
        self.instance.thread = self.commented_object
        return super().save(*args, **kwargs)


class EditCommentForm(forms.Form):
    content = forms.CharField(max_length=Comment._meta.get_field("content").max_length)
    is_pinned = forms.BooleanField(required=False)

    def __init__(self, user: User, comment: Comment, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.comment = comment

    def clean_content(self) -> str:
        content = clean_content(self.cleaned_data["content"])

        if content != self.comment.content:
            self.comment.ensure_can_edit_content(self.user)

        return content

    def clean_is_pinned(self) -> bool:
        is_pinned = self.cleaned_data.get("is_pinned")

        if is_pinned != self.comment.is_pinned:
            self.comment.ensure_can_pin(self.user)

        return is_pinned

    def save(self) -> Comment:
        self.comment.content = self.cleaned_data.get("content")
        self.comment.is_pinned = self.cleaned_data.get("is_pinned")
        self.comment.save(update_fields=("content", "is_pinned"))
        return self.comment
