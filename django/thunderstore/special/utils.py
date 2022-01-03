import base64
import binascii
import json

import requests
from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.primitives.asymmetric import ec


class UnDerException(Exception):
    ...


class DERStringDecoder:
    def __init__(self, initial_bytes):
        self._buffer = initial_bytes
        self._index = 0

    def remaining_data(self):
        return len(self._buffer) - self._index

    def read(self, length):
        new_index = self._index + length
        if new_index > len(self._buffer):
            raise ValueError(
                "Index is over the buffer index: %d buffer length: %d"
                % (new_index, len(self._buffer))
            )
        result = self._buffer[self._index : new_index]
        self._index = new_index
        return int(result, 16)

    def decode(self):
        comps = [str(x) for x in divmod(self.read(2), 40)]
        v = 0
        while self.remaining_data():
            c = self.read(2)
            v = v * 128 + (c & 0x7F)
            if not (c & 0x80):
                comps.append(str(v))
                v = 0
        decoded = ".".join(comps)
        return decoded


def unpem(pem):
    pem_data = pem.encode() if isinstance(pem, str) else pem

    d = (b"").join(
        [l.strip() for l in pem_data.split(b"\n") if l and not l.startswith(b"-----")]
    )
    return base64.b64decode(d)


def ec_points_from_der(key):
    # Let's unDER
    bits = binascii.hexlify(unpem(key))
    der_data = []
    skip = False
    skip_len = 0
    for bit in range(0, len(bits), 2):
        if skip and skip_len:
            skip_len = skip_len - 2
            if skip_len:
                continue
        if bits[bit : bit + 2] in (b"30", b"06", b"03"):
            skip = False
            object_len = (int(bits[bit + 2 : bit + 4], 16) * 2) + 4
            der_data.append((bits[bit : bit + 2], bits[bit : bit + object_len]))
            if bits[bit : bit + 2] in (b"06", b"03"):
                skip = True
                skip_len = object_len

    # Check that we have the correct key type
    if not DERStringDecoder(der_data[2][1][4:]).decode() == "1.2.840.10045.2.1":
        raise UnDerException("Invalid Key Type")
    # Check that we have the correct ec type
    if not DERStringDecoder(der_data[3][1][4:]).decode() == "1.2.840.10045.3.1.7":
        raise UnDerException("Invalid EC Type")
    # Check that the key is an EC key
    if not der_data[4][1][4:8] in (b"0004", b"0003", b"0002"):
        raise UnDerException("Key is not EC")

    # [4][1][6:] should always be the location of the EC points
    return binascii.unhexlify(der_data[4][1][6:].decode())


def fetch_and_setup_public_key(key_identifier: str):
    public_key_endpoint = requests.request(
        "GET", "https://api.github.com/meta/public_keys/secret_scanning"
    )
    keys = json.loads(public_key_endpoint.content)["public_keys"]
    for k in keys:
        if k["key_identifier"] == key_identifier:
            ec_points = ec_points_from_der(k["key"])
            return backend.load_elliptic_curve_public_bytes(ec.SECP256R1(), ec_points)

    raise Exception("Couldn't find a matching key")
