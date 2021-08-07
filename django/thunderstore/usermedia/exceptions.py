from django.core.exceptions import ValidationError


class S3ConfigurationException(AttributeError):
    def __init__(self):
        super().__init__("Invalid S3 storage configuration")


class S3BucketNameMissingException(AttributeError):
    def __init__(self):
        super().__init__("Invalid S3 storage bucket name")


class S3FileKeyChangedException(ValidationError):
    def __init__(self, expected: str, received: str):
        super().__init__(
            "S3 file key changed during upload.\n"
            f"Expected: {expected}.\n"
            f"Received: {received}",
        )


class InvalidUploadStateException(ValidationError):
    def __init__(self, current: str, expected: str):
        super().__init__(
            f"Invalid upload state. Expected: {expected}; found: {current}",
        )


class UploadTooLargeException(ValidationError):
    def __init__(self, size_received: int, max_size: int):
        super().__init__(
            "Upload size exceeds the maximum allowed size. "
            f"Allowed: {max_size}; received: {size_received}.",
        )


class UploadTooSmallException(ValidationError):
    def __init__(self, size_received: int, min_size: int):
        super().__init__(
            "Upload size is smaller than the minimum allowed size. "
            f"Allowed: {min_size}; received: {size_received}"
        )


class UploadNotExpiredException(ValidationError):
    def __init__(self):
        super().__init__("Upload has not yet expired")
