from django.core.exceptions import ValidationError


class PermissionValidationError(ValidationError):
    def __init__(self, message=None, code=None, is_public=True, **kwargs):
        self.is_public = is_public
        super().__init__(message, code, **kwargs)
