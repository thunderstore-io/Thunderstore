class S3ConfigurationException(Exception):
    def __init__(self):
        super().__init__("Invalid S3 storage configuration")


class S3BucketNameMissingException(Exception):
    def __init__(self):
        super().__init__("Invalid S3 storage bucket name")
