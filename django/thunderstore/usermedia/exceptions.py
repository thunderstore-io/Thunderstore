class S3ConfigurationException(Exception):
    def __init__(self):
        super().__init__("Invalid S3 storage configuration")


class S3BucketNameMissingException(Exception):
    def __init__(self):
        super().__init__("Invalid S3 storage bucket name")


class S3MultipartUploadSizeMismatchException(Exception):
    def __init__(self):
        super().__init__("Invalid total file size declared")


class S3FileKeyChangedException(Exception):
    def __init__(self, expected: str, received: str):
        super().__init__(
            "S3 file key changed during upload.\n"
            f"Expected: {expected}.\n"
            f"Received: {received}",
        )


class InvalidUploadStateException(Exception):
    def __init__(self, current: str, expected: str):
        super().__init__(
            f"Invalid upload state. Expected: {expected}; found: {current}",
        )


class UploadTooLargeException(Exception):
    def __init__(self, size_received: int, max_size: int):
        super().__init__(
            "Upload size exceeds the maximum allwoed size. "
            f"Allowed: {max_size}; received: {size_received}.",
        )
