import base64
import binascii
import json

import requests
from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.primitives.asymmetric import ec
from six import b, text_type


class DERStringDecoder(object):
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
    if isinstance(pem, text_type):  # pragma: no branch
        pem = pem.encode()

    d = b("").join(
        [l.strip() for l in pem.split(b("\n")) if l and not l.startswith(b("-----"))]
    )
    return base64.b64decode(d)


def ec_points_from_der(key):
    # Let's unDER
    bits = binascii.hexlify(unpem(key))
    # Sequence 1
    assert bits[0:2] == b"30"
    seq_1_len = int(bits[2:4], 16) * 2
    # Sequence 2
    assert bits[4:6] == b"30"
    seq_2_len = int(bits[6:8], 16) * 2
    # Key type
    assert bits[8:10] == b"06"
    key_type_len = int(bits[10:12], 16) * 2
    key_type_value = DERStringDecoder(bits[12 : 12 + key_type_len]).decode()
    # EC Type
    assert bits[12 + key_type_len : 14 + key_type_len] == b"06"
    ec_type_len = int(bits[14 + key_type_len : 16 + key_type_len], 16) * 2
    ec_type_value = DERStringDecoder(
        bits[12 + key_type_len + 4 : 12 + key_type_len + 4 + ec_type_len]
    ).decode()
    # Bit String
    assert (
        bits[
            12
            + key_type_len
            + 4
            + ec_type_len : 12
            + key_type_len
            + 4
            + ec_type_len
            + 2
        ]
        == b"03"
    )
    bit_string_len = (
        int(
            bits[
                12
                + key_type_len
                + 4
                + ec_type_len
                + 2 : 12
                + key_type_len
                + 4
                + ec_type_len
                + 4
            ],
            16,
        )
        * 2
    )
    bit_string_value = bits[
        12
        + key_type_len
        + 4
        + ec_type_len
        + 4 : 12
        + key_type_len
        + 4
        + ec_type_len
        + 4
        + bit_string_len
    ]

    # Check the whole key lenght is what is stated
    assert (seq_1_len + 4) == len(bits)
    # Check the second sequence, containing key info, is as lenghty as stated
    assert (seq_2_len + 4) == len(bits[4 : 12 + key_type_len + 4 + ec_type_len])
    # Check that we have the correct key type
    assert key_type_value == "1.2.840.10045.2.1"
    # Check that we have the correct ec type
    assert ec_type_value == "1.2.840.10045.3.1.7"
    # Check that the key is an EC key
    assert bit_string_value[:4] in (b"0004", b"0003", "0002")

    return binascii.unhexlify(bit_string_value[2:].decode())


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
