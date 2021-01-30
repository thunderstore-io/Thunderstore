from distutils.version import StrictVersion
from typing import Union

import pytest

from thunderstore.repository.models import Package, PackageVersion

from ..package_reference import PackageReference


@pytest.mark.parametrize(
    ("to_parse", "should_raise"),
    [
        (None, True),
        ("someUser-SomePackage", False),
        ("someUser-SomePackage-1.0.2", False),
        ("some-user-that-has-dashes-SomePackage-1.0.6", False),
        ("some-user-that-has-dashes-SomePackage-1.2.23.2.23.0.6", True),
        ("someUser-SomePackage-1.2.3.2", True),
        ("someUser-1.2.3", True),
        ("someUser-", True),
        ("asd", True),
        ("some-user-with-dashers-SomePackage", False),
        ("239423-2fwjeoifjw32023", False),
        ("a-b", False),
        ("a-b-0.0.1", False),
        ("fjwieojfoi wejoiof w", True),
        ("someUser-somePackage-1231203912.43.249234234", False),
        (PackageReference("namespace", "name", "1.0.0"), False),
        ("TheIllustriousMr.Judson-VindictiveRage-1.0.0", False),
        (
            (
                'ewfWJMPFK"#=jf0p29j3fEWJDf+231\'saf#¤)"'
                '!%?I(!")#(¤?)="#!%-VindictiveRage-1.0.0'
            ),
            False,
        ),
    ],
)
def test_parsing(to_parse, should_raise):
    if should_raise:
        with pytest.raises(ValueError):
            PackageReference.parse(to_parse)
    else:
        parsed = str(PackageReference.parse(to_parse))
        assert parsed == str(to_parse)


@pytest.mark.parametrize(
    ("reference_string", "namespace", "name", "version"),
    [
        ("someUser-SomePackage", "someUser", "SomePackage", ""),
        ("someUser-SomePackage-1.0.2", "someUser", "SomePackage", "1.0.2"),
        (
            "some-user-that-has-dashes-SomePackage-1.0.6",
            "some-user-that-has-dashes",
            "SomePackage",
            "1.0.6",
        ),
        (
            "some-user-with-dashers-SomePackage",
            "some-user-with-dashers",
            "SomePackage",
            "",
        ),
        ("239423-2fwjeoifjw32023", "239423", "2fwjeoifjw32023", ""),
        ("a-b", "a", "b", ""),
        ("a-b-0.0.1", "a", "b", "0.0.1"),
        (
            "someUser-somePackage-1231203912.43.249234234",
            "someUser",
            "somePackage",
            "1231203912.43.249234234",
        ),
        ("Tester-0-test-0-0.0.1", "Tester-0-test", "0", "0.0.1"),
    ],
)
def test_reference_component_split(reference_string: str, namespace, name, version):
    reference = PackageReference.parse(reference_string)
    assert reference.namespace == namespace
    assert reference.name == name
    assert reference.version_str == version


def test_equals_another_type():
    a = PackageReference.parse("SomeAuthor-SomePackage-1.0.0")
    assert (a == 49) is False


@pytest.mark.parametrize(
    ("a_str", "b_str", "assertion"),
    [
        ("someUser-SomePackage", "someUser-SomePackage", True),
        ("someUser-SomePackage", "someUser-SomePackage-1.0.0", False),
        ("someUser-SomePackage-1.0.0", "someUser-SomePackage-1.0.0", True),
        (
            "someUser-SomePackage-112312.120931.242392",
            "someUser-SomePackage-112312.120931.242392",
            True,
        ),
        ("someUser-SomePackage-1.0.0", "someUser-SomePackage-1.0.1", False),
        ("someUser-AnotherPackage-1.0.0", "someUser-SomePackage-1.0.0", False),
        ("SomeUser-SomePackage-1.0.0", "someUser-SomePackage-1.0.0", False),
        ("someUser-SomePackage-1.0.0", "someUser-SomePackage-1.1.0", False),
        ("someUser-SomePackage-1.0.0", "someUser-SomePackage-2.0.0", False),
    ],
)
def test_is_same_version(a_str, b_str, assertion):
    a = PackageReference.parse(a_str)
    b = PackageReference.parse(b_str)
    assert (a == b) == assertion
    assert a.is_same_version(b) == assertion
    assert (str(a) == str(b)) == assertion
    assert str(a) == a_str
    assert str(b) == b_str


@pytest.mark.parametrize(
    ("a_str", "b_str", "assertion"),
    [
        ("someUser-SomePackage", "someUser-SomePackage", True),
        ("someUser-SomePackage", "someUser-SomePackage-1.0.0", True),
        ("someUser-SomePackage", "someUser-SomePackage-1.2.0", True),
        ("someUser-SomePackage", "someUser-SomePackage-1.2.4", True),
        ("someUser-SomePackage", "someUser-SomePackage-0.2.4", True),
        ("someUser-SomePackage", "someUser-SomePackages-0.2.4", False),
        ("someUser-SomePackages", "someUser-SomePackages-0.2.4", True),
        ("asd-SomePackages", "someUser-SomePackages-0.2.4", False),
        ("someUser-SomePackages-2.0.2", "someUser-SomePackages-0.2.4", True),
        ("someUser-SomePackages-423.0.2", "someUser-SomePackages-0.2.4", True),
    ],
)
def test_is_same_package(a_str, b_str, assertion):
    a = PackageReference.parse(a_str)
    b = PackageReference.parse(b_str)
    assert a.is_same_package(b) == assertion
    assert str(a) == a_str
    assert str(b) == b_str


@pytest.mark.parametrize(
    ("inp", "out"),
    [
        ("someUser-SomePackage", "someUser-SomePackage"),
        ("someUser-SomePackage-1.3.2", "someUser-SomePackage"),
        ("someUser-SomePackage-345.231.42", "someUser-SomePackage"),
        ("Ads-Dsa-121.321.31", "Ads-Dsa"),
    ],
)
def test_without_version(inp, out):
    inp = PackageReference.parse(inp)
    out = PackageReference.parse(out)
    assert inp.without_version == out


@pytest.mark.parametrize(
    ("inp", "version", "out", "exc"),
    [
        ("user-package", "1.0.0", "user-package-1.0.0", ""),
        ("user-package", "2.0.0", "user-package-2.0.0", ""),
        ("user-package", "2.6.0", "user-package-2.6.0", ""),
        ("user-package", "asdasdasd", "user-package-2.6.0", "invalid version number"),
    ],
)
def test_with_version(inp: str, version: Union[int, str], out: str, exc: str):
    reference = PackageReference.parse(inp)
    if exc:
        with pytest.raises(ValueError) as exception:
            reference.with_version(version)
        assert exc in str(exception.value)
    else:
        versioned = reference.with_version(version)
        assert versioned == PackageReference.parse(out)
        assert versioned.without_version == reference


@pytest.mark.parametrize(
    ("a_str", "b_str", "should_equal"),
    [
        ("package-user-1.0.0", "package-user-1.0.0", True),
        ("package-user-1.0.0", "package-user-2.0.0", False),
        ("package-user", "package-user", True),
        ("package-user", "package-anotheruser", False),
        ("package-anotheruser", "package-anotheruser", True),
        ("package-anotheruser", "package-anotheruser-493.323.4232", False),
        ("package-anotheruser-4.3.42", "package-anotheruser-4.3.42", True),
        ("pack-anotheruser", "pack-anotheruser", True),
    ],
)
def test_hash_matching(a_str, b_str, should_equal):
    a = PackageReference.parse(a_str)
    b = PackageReference.parse(b_str)
    assert (hash(a) == hash(b)) == should_equal


@pytest.mark.parametrize(
    ("version_number", "should_raise"),
    [
        ("101", True),
        ("101.asdas.wfefwe", True),
        ("101.3223.2323", False),
        (StrictVersion("1.0.1"), False),
    ],
)
def test_init_version_parsing(version_number: str, should_raise: bool):
    if should_raise:
        with pytest.raises(ValueError):
            PackageReference("User", "package", version_number)
    else:
        reference = PackageReference("User", "package", version_number)
        version = ".".join(str(x) for x in reference.version.version)
        assert version == version_number


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("user-pack-1.0.0", "user-pack-1.1.0", False),
        ("user-pack-2.0.0", "user-pack-1.1.0", True),
        (
            "user-pack-1.0.0",
            "user-another-1.1.0",
            "Unable to compare different packages",
        ),
        ("user-pack-1.0.0", "user-pack", "Unable to compare packages without version"),
        ("user-pack", "user-pack-1.0.0", "Unable to compare packages without version"),
        ("user-pack-1.0.0", 10, "Unable to make comparison"),
    ],
)
def test_greater_than(a: str, b: str, expected: Union[bool, str]):
    a = PackageReference.parse(a) if isinstance(a, str) else a
    b = PackageReference.parse(b) if isinstance(b, str) else b
    if isinstance(expected, bool):
        assert (a > b) == expected
    else:
        with pytest.raises(TypeError) as exception:
            _ = a > b
        assert expected in str(exception.value)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("user-pack-1.0.0", "user-pack-1.1.0", True),
        ("user-pack-2.0.0", "user-pack-1.1.0", False),
        (
            "user-pack-1.0.0",
            "user-another-1.1.0",
            "Unable to compare different packages",
        ),
        ("user-pack-1.0.0", "user-pack", "Unable to compare packages without version"),
        ("user-pack", "user-pack-1.0.0", "Unable to compare packages without version"),
        ("user-pack-1.0.0", 10, "Unable to make comparison"),
    ],
)
def test_lesser_than(a: str, b: str, expected: Union[bool, str]):
    a = PackageReference.parse(a) if isinstance(a, str) else a
    b = PackageReference.parse(b) if isinstance(b, str) else b
    if isinstance(expected, bool):
        assert (a < b) == expected
    else:
        with pytest.raises(TypeError) as exception:
            _ = a < b
        assert expected in str(exception.value)


@pytest.mark.parametrize(
    ("reference", "correct"),
    [
        ("user-package-1.0.0", "<PackageReference: user-package-1.0.0>"),
        ("user-package-1.2.0", "<PackageReference: user-package-1.2.0>"),
        ("user-package-1.2.4", "<PackageReference: user-package-1.2.4>"),
        ("user-package", "<PackageReference: user-package>"),
        ("user-SomePackages", "<PackageReference: user-SomePackages>"),
        ("asd-SomePackages", "<PackageReference: asd-SomePackages>"),
    ],
)
def test_repr(reference, correct):
    assert repr(PackageReference.parse(reference)) == correct


def test_string_reference_compatibility():
    reference = PackageReference.parse("user-package-1.0.0")
    assert reference.is_same_package("user-package")
    assert reference.is_same_version("user-package-1.0.0")
    assert not reference.is_same_package("user-package2")
    assert not reference.is_same_version("user-package-1.0.1")


@pytest.mark.django_db
def test_resolve_package_version(package_version: PackageVersion):
    assert package_version.reference.package_version == package_version
    versionless_reference = package_version.reference.without_version
    with pytest.raises(TypeError):
        assert versionless_reference.package_version
    assert versionless_reference.package == package_version.package
    invalid_reference = PackageReference(
        namespace=package_version.reference.namespace,
        name=package_version.reference.name + "invalid",
        version=package_version.reference.version,
    )
    assert invalid_reference.package is None


@pytest.mark.django_db
def test_resolve_package(package: Package):
    assert package.reference.package == package
    invalid_reference = PackageReference(
        namespace=package.reference.namespace,
        name=package.reference.name + "invalid",
        version=package.reference.version,
    )
    assert invalid_reference.package is None


@pytest.mark.django_db
def test_resolve(package_version: PackageVersion):
    assert package_version.reference.package_version == package_version
    assert package_version.reference.instance == package_version
    versionless_reference = package_version.reference.without_version
    assert versionless_reference.package == package_version.package
    assert versionless_reference.instance == package_version.package
    invalid_reference = PackageReference(
        namespace=package_version.reference.namespace,
        name=package_version.reference.name + "invalid",
        version=package_version.reference.version,
    )
    assert invalid_reference.instance is None


@pytest.mark.django_db
def test_queryset(package_version: PackageVersion):
    assert package_version.reference.queryset.exists()
    assert package_version.reference.queryset.count() == 1
    assert package_version.reference.queryset.first() == package_version
    versionless = package_version.reference.without_version
    assert versionless.queryset.exists()
    assert versionless.queryset.count() == 1
    assert versionless.queryset.first() == package_version.package
    invalid = PackageReference("user", "name", "1.0.0")
    assert invalid.queryset.count() == 0
    assert invalid.without_version.queryset.count() == 0


@pytest.mark.django_db
def test_exists(package_version: PackageVersion):
    assert package_version.reference.exists
    assert package_version.reference.without_version.exists
    invalid = PackageReference("user", "name", "1.0.0")
    assert not invalid.exists
    assert not invalid.without_version.exists
