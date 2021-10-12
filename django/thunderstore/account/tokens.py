"""
Tokens adhering to GitHub's token formats:
https://github.blog/2021-04-05-behind-githubs-new-authentication-token-formats/

Main point is to become part of the Github's "Secret scanning program"
to avoid modders placing their sensitive tokens into their public
repos.
"""
from binascii import crc32
from random import choices
from string import ascii_lowercase, ascii_uppercase, digits

from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.utils import baseconv

# Token prefixes, starting with two letter company identifier and
# ending with one letter token type identifier.
SA_TOKEN = "tss"  # Service Account API token


def get_service_account_api_token() -> str:
    """
    ServiceAccount API tokens can be used to e.g. publish new mod
    versions via webhooks.
    """
    payload = get_token_payload(30)
    checksum = get_token_checksum(payload)
    return f"{SA_TOKEN}_{payload}{checksum}"


def get_token_checksum(payload: str, min_length: int = 6) -> str:
    checksum = crc32(payload.encode())
    b62 = baseconv.base62.encode(checksum)
    return b62.rjust(min_length, "0")


def get_token_payload(length: int) -> str:
    alphanumerics = list(ascii_lowercase + ascii_uppercase + digits)
    chars = choices(alphanumerics, k=length)
    return "".join(chars)


def hash_service_account_api_token(token: str) -> str:
    """
    Hash sensitive token for storing in database.

    While using fixed salt and iteration count weakens the protection
    provided by hashing, it's done here as a compromise to make it
    practical to search the service account table based on the token
    when the owner of the token is not known.
    """
    hasher = PBKDF2PasswordHasher()
    salt = "w520TEzFVlsO"
    iterations = 524288
    return hasher.encode(token, salt, iterations)
