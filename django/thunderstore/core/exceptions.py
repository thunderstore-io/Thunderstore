from django.core.exceptions import ValidationError


class PermissionValidationError(ValidationError):
    pass
