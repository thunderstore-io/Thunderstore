import jwt
import pytest

from django.contrib.auth import get_user_model

from core.models import IncomingJWTAuthConfiguration, SecretTypeChoices

User = get_user_model()


TEST_PRIVATE_KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpgIBAAKCAQEA+980zeNCMdA46MXH4kMGp5PYqy35w+Irg9yb8+CFeQ3cWPXc
kKPtWBkrKhgfn0l5D3PIAmCqXqjzM3JuTobDHesJfdrUhZHGflmwY+k2pqyhM61X
iv4NqzmHcHsvXuR0dQ0YeEqnny/d6VQy9ArNZodGDc/MkI8XtCNuU4RY0UWDY/Ay
+qkex15XEyIYk0s8IkJRTLAE1PCwgSUfHaA9FwPDLGPWir+s6nlnY50dN7zcaXv7
7Ay48V2ZrUppCv7n9GvJj2wWXqN5Fo4Yi2muEFG9XFgRx5/kEjicIYGM2EmRiuIp
+KZ3wjKt+CWyYRTdc0dItHxGi4ifzeGyw6haswIDAQABAoIBAQDggxwckoDEymiQ
BQyhgUGDSuSN4dOLaiWDyrgw8WfIejR6D95mB9le+EBjq1E0uVdyELCufeAftNXk
fBIbaUCvgHzbdJ6P2Vtn8SasSIvwkly3JcKtILyqbgNunj+hhF7Sn7O6NkGoQhC7
FdS9eIuS4u3tDde42/QzHIoRZB2Pm3RI0w6Fbq6QKnTIjgcxFoUXNynmzgFMNaoa
FJpzaszVI2dtDxGyptbCz1uOcJ6zS/v0Hk32UHMKMiehgP7lFovqC0ofcAFGKQDt
+G3JKlb9Z6LGBNnSrRZ5pVuRAd8m74gcUdgUDRr9cEFFa+eOfKGIo/Zc8L/vxvMC
fOke6Q2BAoGBAP+COcm+UoXMqBsTuQjdFAj5MFzOs600EC1wZBOZ1UH2rb7lN1lc
fV27IJi/xrv9XR2IDO7bMZrNz+kPG/Ei8AS9HrUO5sCiZMQZB1D31zau1YlnZOGz
KRbksUMqXArxyJk3vlu+M2s7S/+3AtLBFbS0p0X4PUGY+BXpM+gici6TAoGBAPxb
MLixGfThHYKZdYaGsjmqL72MUOIqrQCJvC2rcApMPGeTr11idSMDiHUuszz8zQqP
mWi9LiDe3IkQyEhBAr6UAYD1ZNMVV8S6GsbVUEJbb1qBGD6WThOxc5ZS0yf9zi4T
3qTO4OONB95R5/spPOwE5n+f2DV0zw1EAoTW5JdhAoGBAJk+9v/8Sax8ShsrYiBh
0KFtK8eOJg/tGQLX1P44lsKgfCbxfZf4NCzijjNvWnfoB1AuCGu+ResuI9QJvt2K
8eA1udQoYtgIzl0bEdtLOuZOSD7IJ6aC+VMEyRiasGfUCldzKpYF5vsaroNptaTI
MAeZDnaV48+TOsCRhRNmjYtHAoGBAOnzTG7c2Ph5vpb118u4kf/9s7ahH9ccwzgt
eMRKHFufo5xOgRQtE/U68EXa3pYas6gnyowcXmhg08lKQrMhef7eTaqVVTyPm8eo
1Owik/6Ar/ISnjxfsdB2AXeKH3ICzSNQjmbx1/F9LJ9CBbOF3pHcVShaMuIUAWQF
+ePXKSLhAoGBAL53nGUDh11eB20eISpMDYbUesAPLO/4iCCAhaqLZnia0b6wbcC3
Z44tiM5kqMTfldu+mXfiLmptEO2rgjhtX2jnpNBfyl2kWU5WkUKFnOFFia41L188
tQjSC0si9epWZQjub0+rq6MkOz36Fav7X16ygQzfXXKxuBUoptTCOgQd
-----END RSA PRIVATE KEY-----
""".strip()
TEST_PRIVATE_KEY_2 = """
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAyLDE6vvl1ltX1UZsOXs33pHJmGlkxfpRl621zOvKndWzxc31
BD3MpTfpLcEXdOVNITPDzKgi4vUbRpwg9RCgUa3nb004nC/SX2RsLF2MZN1mR34o
+uYs2UZacv3fx2yFG9t3nITW8DDZdSCMJ5DIY9IS82JOwceL9+Xt902SQcr8dY6S
NS4qnCkD0v9aztPLIuT5FCPmNnLNfcpSDuKFSEJT91C4TkLV6+fiSYBgKLvSJoej
Vb07AmRZB3WzEdniZUhrYwvYuFoF9iSC0XjdEm5WtJzJILG/Pdwu+mrXOKsB9KFb
kKuSWVTLpLAg5LnuIgDbtht/PumggqzpAJXJtQIDAQABAoIBACOUi2TpwebODPVn
5doPCWmxSR93WAFtjreoeXnaN/Lhp1yjVhQpbLXCAto0yJbV7GW9irInAQBh2jMb
jRBFoVa50TU/aJDwPYjiAfefojtjsTVtnZBV7I+c1H5cmib+C19T+pHKT10IHBWS
7qY5Gf3wiaGSxUm/ugX6QsU8gHifVuBHa3oNGEPxJ4Wp9ClAkqrbP5SWhEFNCiRk
fuQURHrmyuRqUAW7DmySpTftYtlgvCaGxuEzCBib/HK3gu4DXNXoYDjFGnRrb2P3
cuWF9OifILpgutgmhcvhLsJeSFxD1Ky0I86CReAWgPJg7BTQoczmUUIZO67pUmZN
ZWrVncECgYEA5Xp4/Qml77XilzekOP364UyFQhutdbA5bed6D0Pn4nmbv9cFJQe3
C+YmRgIKsdifPEySMiHSXeRkUSEGybr78njpUQ50rV3nHibsMCP1/lQNltcFpnnn
lAPyykJcBHssQGdZc89TOxBsG6udn1Hzb6D/8hW3T8xMaTP5TbciWyUCgYEA3+KO
IURI1aK2ihGeNDsS3JYP0FslUWVYNavNtbnKN6hZ/zOMJN4ssRyJaMDvhxPcZFZ3
2Ima8ajkwL2QKriqGOBhhgvDwkn+Iqwlr6g5/3MihVtunKwXcHd41d4hOgSt3Rpt
dclzkKwooEQegQGbaATHlF9F+6rR48oAh4/6N1ECgYBDxY7T1DSgfcwEstcaSc/9
F9dHNdtdpYTgc3t15K0oEpgv6PXJAOVLa1YkWNgFvB8S9N48VgbF2fzShPl3PHTK
IHFvkeBdjx0Bp6cbdJNi4Dn/MVOm3dvJt/zNRRnd7O6duqgNbs565Be5eE6dzdsi
PZ85RLaVp5VtgH8BN7O6zQKBgC3FDTVz1kgGibbUPzmCUirSas03tPtc8pmWU+mw
38xdGHj5us7WtOBIazcFKnK89rN0ke+swgZhdtKIbm6tbejEBmv2/8A6jD/eXZ35
kFHO4eHNfWF+NRSC+CsQzE4mIr0u5+3Kj1umNm/9PRc2kuTDBWIp0A7RLzOYWl9c
adThAoGBAJRq5IM7T0SjJiYSNEGn/kkeEY4SX+fxElsCKfiJ8KeM6B9p/cLCp5Ar
SKpfBzgWWXRXKoTAMuBNykPaCvagqXQ8FmjtsDBY3ypMEfFqwDtY7d4IkahOuD8/
77ozjM0cnNTrKhNmabfPvGzFfWJMUKWU7MBkpSmPuCxwYU03/hoW
-----END RSA PRIVATE KEY-----
""".strip()
TEST_PUBLIC_KEY = """
-----BEGIN RSA PUBLIC KEY-----
MIIBCgKCAQEA+980zeNCMdA46MXH4kMGp5PYqy35w+Irg9yb8+CFeQ3cWPXckKPt
WBkrKhgfn0l5D3PIAmCqXqjzM3JuTobDHesJfdrUhZHGflmwY+k2pqyhM61Xiv4N
qzmHcHsvXuR0dQ0YeEqnny/d6VQy9ArNZodGDc/MkI8XtCNuU4RY0UWDY/Ay+qke
x15XEyIYk0s8IkJRTLAE1PCwgSUfHaA9FwPDLGPWir+s6nlnY50dN7zcaXv77Ay4
8V2ZrUppCv7n9GvJj2wWXqN5Fo4Yi2muEFG9XFgRx5/kEjicIYGM2EmRiuIp+KZ3
wjKt+CWyYRTdc0dItHxGi4ifzeGyw6haswIDAQAB
-----END RSA PUBLIC KEY-----
""".strip()
TEST_PUBLIC_KEY_2 = """
-----BEGIN RSA PUBLIC KEY-----
MIIBCgKCAQEAyLDE6vvl1ltX1UZsOXs33pHJmGlkxfpRl621zOvKndWzxc31BD3M
pTfpLcEXdOVNITPDzKgi4vUbRpwg9RCgUa3nb004nC/SX2RsLF2MZN1mR34o+uYs
2UZacv3fx2yFG9t3nITW8DDZdSCMJ5DIY9IS82JOwceL9+Xt902SQcr8dY6SNS4q
nCkD0v9aztPLIuT5FCPmNnLNfcpSDuKFSEJT91C4TkLV6+fiSYBgKLvSJoejVb07
AmRZB3WzEdniZUhrYwvYuFoF9iSC0XjdEm5WtJzJILG/Pdwu+mrXOKsB9KFbkKuS
WVTLpLAg5LnuIgDbtht/PumggqzpAJXJtQIDAQAB
-----END RSA PUBLIC KEY-----
""".strip()


@pytest.mark.django_db
def test_jwt_hs256_decode_incoming_valid():
    jwt_secret = "superSecret"
    user = User.objects.create_user(
        username="Test",
        email="test@example.org",
        password="hunter2",
    )
    auth = IncomingJWTAuthConfiguration.objects.create(
        name="Test configuration",
        user=user,
        secret=jwt_secret,
        secret_type=SecretTypeChoices.hs256,
    )

    payload = {"test": "data"}
    encoded = jwt.encode(payload, jwt_secret, algorithm=SecretTypeChoices.hs256)
    result = IncomingJWTAuthConfiguration.decode_incoming_data(encoded, auth.key_id)
    assert len(result) == 2
    assert result["user"] == user
    assert result["data"] == payload


@pytest.mark.django_db
def test_jwt_hs256_decode_incoming_invalid():
    user = User.objects.create_user(
        username="Test",
        email="test@example.org",
        password="hunter2",
    )
    auth = IncomingJWTAuthConfiguration.objects.create(
        name="Test configuration",
        user=user,
        secret="superSecret",
        secret_type=SecretTypeChoices.hs256,
    )

    payload = {"test": "data"}
    encoded = jwt.encode(payload, "notCorrect", algorithm=SecretTypeChoices.hs256)
    with pytest.raises(jwt.exceptions.InvalidTokenError):
        IncomingJWTAuthConfiguration.decode_incoming_data(encoded, auth.key_id)


@pytest.mark.django_db
def test_jwt_rs256_decode_incoming_valid():
    user = User.objects.create_user(
        username="Test",
        email="test@example.org",
        password="hunter2",
    )
    auth = IncomingJWTAuthConfiguration.objects.create(
        name="Test configuration",
        user=user,
        secret=TEST_PUBLIC_KEY,
        secret_type=SecretTypeChoices.rs256,
    )

    payload = {"test": "data"}
    encoded = jwt.encode(payload, TEST_PRIVATE_KEY, algorithm=SecretTypeChoices.rs256)
    result = IncomingJWTAuthConfiguration.decode_incoming_data(encoded, auth.key_id)
    assert len(result) == 2
    assert result["user"] == user
    assert result["data"] == payload


@pytest.mark.django_db
def test_jwt_rs256_decode_incoming_invalid():
    user = User.objects.create_user(
        username="Test",
        email="test@example.org",
        password="hunter2",
    )
    auth = IncomingJWTAuthConfiguration.objects.create(
        name="Test configuration",
        user=user,
        secret=TEST_PUBLIC_KEY_2,
        secret_type=SecretTypeChoices.rs256,
    )

    payload = {"test": "data"}
    encoded = jwt.encode(payload, TEST_PRIVATE_KEY, algorithm=SecretTypeChoices.rs256)
    with pytest.raises(jwt.exceptions.InvalidTokenError):
        IncomingJWTAuthConfiguration.decode_incoming_data(encoded, auth.key_id)
