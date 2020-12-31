import re

AUTHOR_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\_\.\-]+$")
PACKAGE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\_]+$")
PACKAGE_VERSION_REGEX = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
